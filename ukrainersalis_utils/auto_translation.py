import asyncio
import os
import re
from typing import Tuple

from dotenv import load_dotenv

from ukrainersalis_utils.gemini_translator import GeminiTranslator, RU_UA_SYSTEM_INSTRUCTION
from ukrainersalis_utils.logger import logger
from ukrainersalis_utils.translators.translation_api import Translator
from ukrainersalis_utils.utils.file_utils import list_localization_files
from ukrainersalis_utils.utils.yaml_utils import write_eu5_localization_yaml_async, load_eu5_yaml_async, \
    validate_localization_file

_NEWLINE_REPLANCEMENT = "#NL!#"


def translation_preprocessing(line: str) -> str:
    line = line.replace("\n", _NEWLINE_REPLANCEMENT)
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
    line = expand_concepts(line)
    line = expand_adjectives(line)
    line = line.replace(_NEWLINE_REPLANCEMENT, "\n")
    return line


async def translate_file(input_file_path: str, output_file_path: str, output_dir: str,
                         translator: Translator, semaphore: asyncio.Semaphore,
                         source_language: str = "english") -> bool:
    """Translate a single file asynchronously.

    Returns:
        True if translation succeeded, False otherwise
    """
    file_name = os.path.basename(input_file_path)
    output_file_name = os.path.basename(output_file_path)

    try:
        async with semaphore:
            # Read file
            content = await load_eu5_yaml_async(input_file_path)
            localization = content.get(f"l_{source_language}", {})
            lines = "\n".join([translation_preprocessing(l) for l in localization.values()])

            logger.info(f"Translating {input_file_path}")
            translation = await translator.translate_async(lines)
            translation = translation.splitlines()

            for key, value in zip(localization.keys(), translation):
                translated_value = translation_postprocessing(value)
                if translated_value == "" and value != "":
                    logger.warning(f"Empty translation for {key} in {file_name}, potentially a translation glitch")
                    translated_value = "POSTEDIT_EMPTY_TRANSLATION"
                localization[key] = translated_value

            # Create output directory if needed
            await asyncio.to_thread(os.makedirs, output_dir, exist_ok=True)
            await write_eu5_localization_yaml_async(content, output_file_path)
            logger.info(f"Translated {file_name} -> {output_file_name}")
            return True

    except Exception as e:
        logger.exception(f"Error processing {file_name}: {e}")
        return False


def _find_untranslated_files(max_translations: int, overwrite_existing_translation: bool = False,
                             source_language: str = "english", target_language: str = "ukrainian",
                             translation_suffix: str = "machine_translation") -> list[Tuple[str, str, str]]:
    files_to_translate: list[Tuple[str, str, str]] = []
    english_files = list_localization_files(source_language)
    for input_file_path in english_files:
        input_dir_path, file_name = os.path.split(input_file_path)
        output_dir_path = input_dir_path.replace(f"/{source_language}", f"/{target_language}")
        output_file_name = file_name.replace(f"_l_{source_language}.yml", f"_l_{target_language}_{translation_suffix}.yml")
        output_file_path = os.path.join(output_dir_path, output_file_name)

        if os.path.exists(output_file_path) and not overwrite_existing_translation:
            logger.info(f"Skipping {file_name} -> {output_file_name} (already exists)")
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
                              source_language: str = "english", target_language: str = "ukrainian",
                              translation_suffix: str = "machine_translation"):
    """Translate all English localization files in directory tree asynchronously.

    Args:
        dir_path: Root directory to search for translation files
        translator: Translator instance to use
        max_files_to_translate: Maximum number of files to translate (None for unlimited)
        overwrite_existing_translation: Whether to overwrite existing translations
        max_concurrency: Maximum number of concurrent translation tasks
        source_language: Source language of the files to translate
        target_language: Target language for the translations
        translation_suffix: Suffix to append to the output file names
    """
    # Collect all files to translate
    files_to_translate = _find_untranslated_files(max_files_to_translate, overwrite_existing_translation, source_language, target_language, translation_suffix)

    # Setting up concurrency
    semaphore = asyncio.Semaphore(max_concurrency)
    tasks = [
        translate_file(input_path, output_path, output_dir, translator, semaphore, source_language=source_language)
        for input_path, output_path, output_dir in files_to_translate
    ]

    # Execute all tasks concurrently
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Count successful translations
    successful = sum(1 for r in results if r is True)
    logger.info(f"Completed: {successful}/{len(files_to_translate)} files translated successfully")


if __name__ == '__main__':
    load_dotenv()
    _translator = GeminiTranslator(system_instruction=RU_UA_SYSTEM_INSTRUCTION)
    asyncio.run(translate_dir_async(
        _translator, max_files_to_translate=512, overwrite_existing_translation=False,
        source_language="russian", target_language="russian", translation_suffix="uk_ua_machine_translation"))
