import asyncio
import copy
import json
import os
import re
from pathlib import Path
from typing import Tuple

from dotenv import load_dotenv

from eukrainersalis.translators.gemini_translator import GeminiTranslator
from eukrainersalis.translators.translator_api import Translator
from eukrainersalis.utils.file_utils import list_localization_files, project_dir
from eukrainersalis.utils.log_utils import logger
from eukrainersalis.utils.migration_utils import MigrationManager
from eukrainersalis.utils.translation_utils import POSTEDIT_EMPTY_TRANSLATION, PENDING_TRANSLATION, \
    text_is_not_translated, translation_is_required, translation_not_required, Language, SystemInstruction
from eukrainersalis.utils.yaml_utils import write_eu5_localization_yaml_async, load_eu5_yaml_async, \
    validate_localization_file, file_is_translated, load_eu5_yaml, write_eu5_localization_yaml

_NEWLINE_REPLANCEMENT = "#NL!#"
_DEFAULT_SOURCE_LANGUAGE = Language.ENGLISH
_DEFAULT_TARGET_LANGUAGE = Language.ENGLISH
_DEFAULT_MACHINE_SUFFIX = "machine_translation"

_PREPROC_MAPPINGS = {
    # 1.1.10 -> 1.2.0
    "'fem'": "'end_fem'",
    "'enna'": "'end_enna'",
    "'etut'": "'end_etut'",
    "'etyut'": "'end_etyut'",
    "'gegu'": "'end_gegu'",
    "'itat'": "'end_itat'",
    "'ityat'": "'end_ityat'",
    "'assya'": "'end_assya'",
    "…": "...",
}

_EXCLUDED_FILES = [
    "customizable_localization_end",
]


_migration_manager = MigrationManager("1.1.10")


def translation_preprocessing(line: str) -> str:
    # line = line.replace("\n", _NEWLINE_REPLANCEMENT)
    return line


def migration_value_preprocessing(value: str) -> str:
    preprocessed = value
    for k, v in _PREPROC_MAPPINGS.items():
        preprocessed = preprocessed.replace(k, v)
    return preprocessed


def migration_diff_detected(input_file_path, reference_file_path, language_key: str | None = None, migration_mappings: dict[str, str] | None = None):
    """
    Check if there's a difference between older and current file versions,
    and if the file needs to be migrated.
    """
    if _migration_manager.is_migrated(input_file_path):
        return False

    localization_key = language_key or Language.RUSSIAN.localization_key
    input_localization = load_eu5_yaml(input_file_path).get(localization_key, {})
    ref_localization = load_eu5_yaml(reference_file_path).get(localization_key, {})

    migrated_localization = {}
    input_remapped = False
    change_detected = False
    for key, value in input_localization.items():
        orig_value = input_localization[key]
        in_value = migration_value_preprocessing(orig_value)
        migrated_localization[key] = in_value

        # TODO: scenario where records are deleted relative to reference - change detected

        if not input_remapped and orig_value != in_value:
            # migration patch was applied, and the file needs rewriting
            input_remapped = True
        if key in ref_localization:
            if not change_detected:
                ref_value = migration_value_preprocessing(ref_localization[key])
                change_detected = in_value != ref_value
        else:
            # new key - change detected
            change_detected = True

    if input_remapped:
        content = {localization_key: migrated_localization}
        write_eu5_localization_yaml(content, input_file_path)
    if not change_detected:
        _migration_manager.mark_migrated(input_file_path)

    return change_detected


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


async def create_starting_output_file(content: dict[str, dict], source_language: Language | str, output_file_path: str) -> dict[
    str, dict[str, str]]:
    localization_key = Language(source_language).localization_key
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
) -> tuple[int, int]:
    """Translate one batch and immediately save progress to file."""
    batch_size = len(batch)
    async with api_semaphore:
        lines = [json.dumps({k: v}, ensure_ascii=False) for k, v in batch]
        try:
            translated_lines = await translator.translate_batch_async(lines)
        except Exception as e:
            logger.error(f"Batch {batch_idx + 1}/{total_batches} of {file_name} failed: {e}")
            return -1, batch_size

    successful_translations = 0
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
                        successful_translations += 1

        await write_eu5_localization_yaml_async(translated_content, output_file_path)
        logger.debug(f"Saved batch {batch_idx + 1}/{total_batches} of {file_name}")

    return successful_translations, batch_size


async def translate_file(input_file_path: str, output_file_path: str, output_dir: str,
                         translator: Translator, api_semaphore: asyncio.Semaphore,
                         batch_size: int = 25, source_language: Language | str = Language.ENGLISH,
                         target_language: Language | str = Language.ENGLISH,
                         change_reference_source_dir: Path | None = None) -> int:
    """Translate a single file, writing progress to disk after each batch.

    Returns:
        True if all batches translated successfully, False otherwise.
    """
    file_name = os.path.basename(input_file_path)
    output_file_name = os.path.basename(output_file_path)
    localization_key = Language(source_language).localization_key
    target_localization_key = Language(target_language).localization_key

    rel_path = Path(input_file_path).relative_to(project_dir)
    reference_file_path = change_reference_source_dir / rel_path if change_reference_source_dir else None
    reference_file_path = reference_file_path if reference_file_path and os.path.exists(reference_file_path) else None
    has_reference_file = reference_file_path is not None

    try:
        content = await load_eu5_yaml_async(input_file_path)
        in_localization: dict[str, str] = content.get(localization_key, {})

        ref_content = await load_eu5_yaml_async(str(reference_file_path)) if has_reference_file else {}
        ref_localization: dict[str, str] = ref_content.get(localization_key, {})

        # Setting up translated content
        if not os.path.exists(output_file_path):
            translated_content = await create_starting_output_file(content, source_language, output_file_path)
        else:
            translated_content = await load_eu5_yaml_async(output_file_path)
            translated_localization = translated_content.get(target_localization_key, {})

            # merging source and target, making sure that source structure is preserved
            def merge_key_value(key):
                if key in ref_localization and key in translated_localization:
                    # IF pre- and post-patch values are identical, then no translation is required
                    in_value = migration_value_preprocessing(in_localization[key])
                    ref_value = migration_value_preprocessing(ref_localization[key])
                    if in_value == ref_value:
                        return in_value
                    else:
                        return PENDING_TRANSLATION

                if key in translated_localization:
                    return translated_localization[key]
                elif translation_not_required(in_localization[key]):
                    return in_localization[key]
                else:
                    return PENDING_TRANSLATION

            translated_content[target_localization_key] = {k: merge_key_value(k) for k in in_localization.keys()}

        translated_localization = translated_content.get(target_localization_key, {})
        untranslated_keys = {k: in_localization.get(k) for k, v in translated_localization.items() if
                             text_is_not_translated(v)}
        if len(untranslated_keys) == 0:
            return 0

        batches = _split_into_batches(list(untranslated_keys.items()), batch_size)
        total_batches = len(batches)
        write_lock = asyncio.Lock()

        logger.info(f"Translating {file_name}: {len(untranslated_keys)} phrases in {total_batches} batches")

        tasks = [
            _translate_and_save_batch(
                batch, in_localization, translated_localization, translated_content,
                output_file_path, translator, api_semaphore, write_lock,
                batch_idx, total_batches, file_name,
            )
            for batch_idx, batch in enumerate(batches)
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        successful_translation = sum(r[0] for r in results if r is True)
        if successful_translation == len(untranslated_keys):
            logger.info(f"Translated {file_name} -> {output_file_name}")
        else:
            logger.warning(f"Partial translation {file_name}: {successful_translation}/{len(untranslated_keys)} lines succeeded")
        return successful_translation

    except Exception as e:
        logger.exception(f"Error processing {file_name}: {e}")
        return 0


def _find_untranslated_files(max_translations: int, overwrite_existing_translation: bool = False,
                             source_language: Language | str = Language.ENGLISH,
                             target_language: Language | str = Language.UKRAINIAN,
                             translation_suffix: str = "machine_translation",
                             change_reference_source_dir: Path | None = None) -> list[Tuple[str, str, str]]:
    files_to_translate: list[Tuple[str, str, str]] = []
    source_files = list_localization_files(source_language)
    for input_file_path in source_files:
        input_dir_path, file_name = os.path.split(input_file_path)
        output_dir_path = input_dir_path.replace(f"/{source_language}", f"/{target_language}")
        output_file_name = file_name.replace(f"_l_{source_language}.yml",
                                             f"_l_{target_language}_{translation_suffix}.yml")
        output_file_path = os.path.join(output_dir_path, output_file_name)

        rel_path = Path(input_file_path).relative_to(project_dir)
        reference_file_path = change_reference_source_dir / rel_path if change_reference_source_dir else None
        reference_file_path = reference_file_path if reference_file_path and os.path.exists(reference_file_path) else None
        has_reference_file = reference_file_path is not None

        if has_reference_file and migration_diff_detected(input_file_path, reference_file_path):
            files_to_translate.append((input_file_path, output_file_path, output_dir_path))
            continue

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


async def translate_dir_async(translator: Translator,
                              max_files_to_translate: int | None = None,
                              overwrite_existing_translation: bool = False,
                              max_concurrency: int = 8,
                              batch_size: int = 25,
                              source_language: Language | str = _DEFAULT_SOURCE_LANGUAGE,
                              target_language: Language | str = _DEFAULT_TARGET_LANGUAGE,
                              translation_suffix: str = _DEFAULT_MACHINE_SUFFIX,
                              change_reference_source_dir: Path | None = None):
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
        change_reference_source_dir: If provided, files in the reference directory will be used as change detection reference.
    """
    files_to_translate = _find_untranslated_files(
        max_files_to_translate or 1_000_000, overwrite_existing_translation, source_language, target_language, translation_suffix, change_reference_source_dir
    )

    api_semaphore = asyncio.Semaphore(max_concurrency)
    tasks = [
        translate_file(input_path, output_path, output_dir,
                       translator, api_semaphore, batch_size,
                       source_language, target_language,
                       change_reference_source_dir)
        for input_path, output_path, output_dir in files_to_translate
    ]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    successful = sum(1 for r in results if r is True)
    logger.info(f"Completed: {successful}/{len(files_to_translate)} files translated successfully")


if __name__ == '__main__':
    load_dotenv()
    _translator = GeminiTranslator(system_instruction_config=SystemInstruction.RU_UA)
    asyncio.run(translate_dir_async(
        _translator, max_files_to_translate=1, overwrite_existing_translation=True,
        source_language=Language.RUSSIAN, target_language=Language.RUSSIAN, translation_suffix="uk_ua_machine_translation",
        change_reference_source_dir=Path("/home/primislas/workspace/eu5-modding-prev-version")
    ))
