import asyncio
import copy
import json
import os
import re
from typing import Tuple

from dotenv import load_dotenv

from eukrainersalis.translators.gemini_translator import GeminiTranslator, RU_UA_SYSTEM_INSTRUCTION
from eukrainersalis.translators.translator_api import Translator
from eukrainersalis.utils.file_utils import list_localization_files
from eukrainersalis.utils.log_utils import logger
from eukrainersalis.utils.translation_utils import POSTEDIT_EMPTY_TRANSLATION, PENDING_TRANSLATION, \
    text_is_not_translated, translation_is_required, translation_not_required
from eukrainersalis.utils.yaml_utils import write_eu5_localization_yaml_async, load_eu5_yaml_async, \
    validate_localization_file, file_is_translated

_NEWLINE_REPLANCEMENT = "#NL!#"
_DEFAULT_SOURCE_LANGUAGE = "english"
_DEFAULT_TARGET_LANGUAGE = "english"
_DEFAULT_MACHINE_SUFFIX = "machine_translation"


def translation_preprocessing(line: str) -> str:
    # line = line.replace("\n", _NEWLINE_REPLANCEMENT)
    return line


def expand_concepts(line: str) -> str:
    """Expands concepts in the translated text."""
    # Pattern to match [<concept>|e] where <concept> doesn't contain '(' or '|' to avoid double-processing
    # or nested structures if any.
    pattern = r"\[([^()\[\]|]+)\|[eE]\]"
    replacement = r"[Concept('\1', 'CONCEPT_PLACEHOLDER')|e]"

    return re.sub(pattern, replacement, line)


def expand_adjectives(line: str) -> str:
    """Expands adjectives in the translated text."""
    # Pattern to match constructs like [...GetAdjective...|l] or [...Adjective('...')|l].
    # But it must not contain specific excluded strings.
    # Excluded strings: "AdjectiveWithNoTooltip", ":actor.GetReligion.GetGroup.GetAdjective",
    # "COUNTRY.GetAdjective", "TARGET_COUNTRY.GetAdjective"

    pattern = r"\[[^\]]*(?:GetAdjective|Adjective\('[^']*'\))[^\]]*\|l\]"

    def replacement(match):
        matched_value = match.group(0)
        exclusions = [
            "AdjectiveWithNoTooltip",
            ":actor.GetReligion.GetGroup.GetAdjective",
            "COUNTRY.GetAdjective",
            "TARGET_COUNTRY.GetAdjective"
        ]
        for exclusion in exclusions:
            if exclusion in matched_value:
                return matched_value
        return f"#L {matched_value}#!"

    return re.sub(pattern, replacement, line)


def translation_postprocessing(line: str) -> str:
    """Postprocesses the translated text by removing unnecessary characters and formatting."""
    # line = expand_concepts(line)
    # line = expand_adjectives(line)
    # line = line.replace(_NEWLINE_REPLANCEMENT, "\n")
    line = line.replace("\\", "\\\\")
    return line


async def create_starting_output_file(content: dict[str, dict], source_language: str, output_file_path: str) -> dict[
    str, dict[str, str]]:
    localization_key = f"l_{source_language}"
    localization: dict[str, str] = copy.copy(content.get(localization_key, {}))
    for key, value in localization.items():
        if translation_is_required(value):
            localization[key] = PENDING_TRANSLATION
    untranslated_content = {localization_key: localization}
    await write_eu5_localization_yaml_async(untranslated_content, output_file_path)
    logger.info(f"Created untranslated file: {output_file_path}")
    return untranslated_content


def _split_into_batches(items: list, batch_size: int, min_last_batch_size: int = 10) -> list[list]:
    """Split items into batches. Merges the last batch into the previous one if it's too small."""
    batches = [items[i:i + batch_size] for i in range(0, len(items), batch_size)]
    if len(batches) > 1 and len(batches[-1]) < min_last_batch_size:
        last_batch = batches.pop()
        batches[-1].extend(last_batch)
    return batches


async def _translate_and_save_batch(
        batch: list[tuple[str, str]],
        localization: dict[str, str],
        translated_localization: dict[str, str],
        translated_content: dict[str, dict],
        output_file_path: str,
        translator: Translator,
        api_semaphore: asyncio.Semaphore,
        write_lock: asyncio.Lock,
        batch_idx: int,
        total_batches: int,
        file_name: str,
) -> bool:
    """Translate one batch and immediately save progress to file."""
    async with api_semaphore:
        lines = [json.dumps({k: v}, ensure_ascii=False) for k, v in batch]
        try:
            translated_lines = await translator.translate_batch_async(lines)
        except Exception as e:
            logger.error(f"Batch {batch_idx + 1}/{total_batches} of {file_name} failed: {e}")
            return False

    async with write_lock:
        for line in translated_lines:
            lkv: dict[str, str] = {}
            try:
                lkv = json.loads(line)
            except Exception:
                try:
                    # sometimes running into failing escape sequences
                    lkv = json.loads(translation_postprocessing(line))
                except Exception:
                    logger.error(f"Expected a JSON but received: " + line)
            if lkv:
                for k, v in lkv.items():
                    if len(v) == 0 and len(localization.get(k, "")) > 0:
                        translated_localization[k] = POSTEDIT_EMPTY_TRANSLATION
                    else:
                        translated_localization[k] = v

        await write_eu5_localization_yaml_async(translated_content, output_file_path)
        logger.debug(f"Saved batch {batch_idx + 1}/{total_batches} of {file_name}")

    return True


async def translate_file(input_file_path: str, output_file_path: str, output_dir: str,
                         translator: Translator, api_semaphore: asyncio.Semaphore,
                         batch_size: int = 25, source_language: str = "english",
                         target_language: str = "english") -> bool:
    """Translate a single file, writing progress to disk after each batch.

    Returns:
        True if all batches translated successfully, False otherwise.
    """
    file_name = os.path.basename(input_file_path)
    output_file_name = os.path.basename(output_file_path)
    localization_key = f"l_{source_language}"
    target_localization_key = f"l_{target_language}"

    try:
        content = await load_eu5_yaml_async(input_file_path)
        localization: dict[str, str] = content.get(localization_key, {})

        # Setting up translated content
        if not os.path.exists(output_file_path):
            translated_content = await create_starting_output_file(content, source_language, output_file_path)
        else:
            translated_content = await load_eu5_yaml_async(output_file_path)
            translated_localization = translated_content.get(target_localization_key, {})

            # merging source and target, making sure that source structure is preserved
            def merge_key_value(key):
                if key in translated_localization:
                    return translated_localization[key]
                elif translation_not_required(localization[key]):
                    return localization[key]
                else:
                    return PENDING_TRANSLATION

            translated_content[target_localization_key] = {k: merge_key_value(k) for k in localization.keys()}

        translated_localization = translated_content.get(target_localization_key, {})
        untranslated_keys = {k: localization.get(k) for k, v in translated_localization.items() if
                             text_is_not_translated(v)}
        if len(untranslated_keys) == 0:
            return True

        batches = _split_into_batches(list(untranslated_keys.items()), batch_size)
        total_batches = len(batches)
        write_lock = asyncio.Lock()

        logger.info(f"Translating {file_name}: {len(untranslated_keys)} phrases in {total_batches} batches")

        tasks = [
            _translate_and_save_batch(
                batch, localization, translated_localization, translated_content,
                output_file_path, translator, api_semaphore, write_lock,
                batch_idx, total_batches, file_name,
            )
            for batch_idx, batch in enumerate(batches)
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        successful_batches = sum(1 for r in results if r is True)
        if successful_batches == total_batches:
            logger.info(f"Translated {file_name} -> {output_file_name}")
        else:
            logger.warning(f"Partial translation {file_name}: {successful_batches}/{total_batches} batches succeeded")
        return successful_batches == total_batches

    except Exception as e:
        logger.exception(f"Error processing {file_name}: {e}")
        return False


def _find_untranslated_files(max_translations: int, overwrite_existing_translation: bool = False,
                             source_language: str = "english", target_language: str = "ukrainian",
                             translation_suffix: str = "machine_translation") -> list[Tuple[str, str, str]]:
    files_to_translate: list[Tuple[str, str, str]] = []
    source_files = list_localization_files(source_language)
    for input_file_path in source_files:
        input_dir_path, file_name = os.path.split(input_file_path)
        output_dir_path = input_dir_path.replace(f"/{source_language}", f"/{target_language}")
        output_file_name = file_name.replace(f"_l_{source_language}.yml",
                                             f"_l_{target_language}_{translation_suffix}.yml")
        output_file_path = os.path.join(output_dir_path, output_file_name)

        if os.path.exists(output_file_path) and not overwrite_existing_translation and file_is_translated(
                output_file_path, language=target_language):
            logger.info(f"Skipping {file_name} -> {output_file_name} (already translated)")
            continue
        if not validate_localization_file(input_file_path, source_language):
            logger.info(f"Skipping {file_name} -> {output_file_name} (invalid localization file)")
            continue

        files_to_translate.append((input_file_path, output_file_path, output_dir_path))
        if max_translations and len(files_to_translate) >= max_translations:
            break
    logger.info(f"Identified {len(files_to_translate)} files to translate")
    return files_to_translate


async def translate_dir_async(translator: Translator, max_files_to_translate: int | None = None,
                              overwrite_existing_translation: bool = False, max_concurrency: int = 8,
                              batch_size: int = 25,
                              source_language: str = _DEFAULT_SOURCE_LANGUAGE,
                              target_language: str = _DEFAULT_TARGET_LANGUAGE,
                              translation_suffix: str = _DEFAULT_MACHINE_SUFFIX):
    """Translate all localization files in the directory tree.

    Args:
        translator: Translator instance to use.
        max_files_to_translate: Maximum number of files to translate (None for unlimited).
        overwrite_existing_translation: Whether to overwrite existing translations.
        max_concurrency: Maximum number of concurrent API batch calls (shared across all files).
        batch_size: Number of lines per translation batch.
        source_language: Source language of the files to translate.
        target_language: Target language for the translations.
        translation_suffix: Suffix to append to the output file names.
    """
    files_to_translate = _find_untranslated_files(
        max_files_to_translate, overwrite_existing_translation, source_language, target_language, translation_suffix
    )

    api_semaphore = asyncio.Semaphore(max_concurrency)
    tasks = [
        translate_file(input_path, output_path, output_dir,
                       translator, api_semaphore, batch_size,
                       source_language, target_language)
        for input_path, output_path, output_dir in files_to_translate
    ]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    successful = sum(1 for r in results if r is True)
    logger.info(f"Completed: {successful}/{len(files_to_translate)} files translated successfully")


if __name__ == '__main__':
    load_dotenv()
    _translator = GeminiTranslator(system_instruction=RU_UA_SYSTEM_INSTRUCTION)
    asyncio.run(translate_dir_async(
        _translator, max_files_to_translate=512, overwrite_existing_translation=False,
        source_language="russian", target_language="russian", translation_suffix="uk_ua_machine_translation"))
