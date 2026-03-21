import asyncio
import os
import re

import aiofiles
import yaml


class DoubleQuotedDumper(yaml.SafeDumper):
    def represent_mapping(self, tag, mapping, flow_style=None):
        value = []
        node = yaml.nodes.MappingNode(tag, value, flow_style=flow_style)
        if self.alias_key is not None:
            self.represented_objects[self.alias_key] = node
        best_style = True
        if hasattr(mapping, 'items'):
            mapping = list(mapping.items())
            if self.sort_keys:
                mapping.sort(key=lambda x: x[0])
        for item_key, item_value in mapping:
            node_key = self.represent_data(item_key)
            # Remove forcing style on keys
            if isinstance(node_key, yaml.nodes.ScalarNode) and node_key.tag == 'tag:yaml.org,2002:str':
                node_key.style = None
            node_value = self.represent_data(item_value)
            if not (isinstance(node_key, yaml.nodes.ScalarNode) and node_key.style is None):
                best_style = False
            if not (isinstance(node_value, yaml.nodes.ScalarNode) and node_value.style is None):
                best_style = False
            value.append((node_key, node_value))
        if flow_style is None:
            if self.default_flow_style is not None:
                node.flow_style = self.default_flow_style
            else:
                node.flow_style = best_style
        return node


def quoted_str_representer(dumper, data):
    return dumper.represent_scalar('tag:yaml.org,2002:str', data, style='"')


DoubleQuotedDumper.add_representer(str, quoted_str_representer)

from flask.cli import load_dotenv

from ukrainersalis_utils.logger import logger
from ukrainersalis_utils.gemini_translation import GeminiTranslator
from ukrainersalis_utils.translators.translation_api import Translator


_NEWLINE_REPLANCEMENT = "#NL!#"


def translation_preprocessing(line: str) -> str:
    line = line.replace("\n", _NEWLINE_REPLANCEMENT)
    return line


def expand_concepts(line: str) -> str:
    """Expands concepts in the translated text."""
    # Pattern to match [<concept>|e] where <concept> doesn't contain '(' or '|' to avoid double-processing
    # or nested structures if any.
    pattern = r"\[([^()|]+)\|[eE]\]"
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
                         translator: Translator, semaphore: asyncio.Semaphore) -> bool:
    """Translate a single file asynchronously.

    Returns:
        True if translation succeeded, False otherwise
    """
    file_name = os.path.basename(input_file_path)
    output_file_name = os.path.basename(output_file_path)

    try:
        async with semaphore:
            # Read file
            async with aiofiles.open(input_file_path, "r") as file_handle:
                content_str = await file_handle.read()

            content = yaml.load(content_str, Loader=yaml.FullLoader)
            l_english = content.get("l_english")
            if not l_english:
                logger.info(f"Skipping {file_name} -> {output_file_name} (no l_english key)")
                return False

            lines = "\n".join([translation_preprocessing(l) for l in l_english.values()])
            logger.info(f"Translating {input_file_path}")

            # Call async translation method if available, otherwise fall back to sync
            if hasattr(translator, 'translate_async'):
                translation = await translator.translate_async(lines)
            else:
                translation = await asyncio.to_thread(translator.translate, lines)
            translation = translation.splitlines()

            for key, value in zip(l_english.keys(), translation):
                translated_value = translation_postprocessing(value)
                if translated_value == "" and value != "":
                    logger.warning(f"Empty translation for {key} in {file_name}, potentially a translation glitch")
                    translated_value = "POSTEDIT_EMPTY_TRANSLATION"
                l_english[key] = translated_value

            # Create output directory if needed
            await asyncio.to_thread(os.makedirs, output_dir, exist_ok=True)

            # Write file
            dumped = yaml.dump(
                content,
                Dumper=DoubleQuotedDumper,
                allow_unicode=True,
                sort_keys=False,
                width=float('inf'),
            )
            async with aiofiles.open(output_file_path, "w") as output_file_handle:
                await output_file_handle.write(dumped.strip())

            logger.info(f"Translated {file_name} -> {output_file_name}")
            return True

    except Exception as e:
        logger.exception(f"Error processing {file_name}: {e}")
        return False


def _validate_yaml_file(file_path: str) -> bool:
    """Validate a YAML file by parsing it and checking for errors."""
    try:
        with open(file_path, "r") as file_handle:
            content = yaml.load(file_handle, Loader=yaml.FullLoader)
        return "l_english" in content
    except Exception:
        logger.exception(f"Error parsing {file_path}")
        return False


async def translate_dir_async(dir_path: str, translator: Translator, max_translations: int | None = None,
                               overwrite_existing_translation: bool = False, max_concurrency: int = 8):
    """Translate all English localization files in directory tree asynchronously.

    Args:
        dir_path: Root directory to search for translation files
        translator: Translator instance to use
        max_translations: Maximum number of files to translate (None for unlimited)
        overwrite_existing_translation: Whether to overwrite existing translations
        max_concurrency: Maximum number of concurrent translation tasks
    """
    # Collect all files to translate
    files_to_translate = []

    for root, dirs, files in os.walk(dir_path):
        for file_name in files:
            if not "_l_english" in file_name or not file_name.endswith(".yml"):
                continue

            input_file_path = os.path.join(root, file_name)
            output_dir = root.replace("/english", "/ukrainian")
            output_file_name = file_name.replace("_l_english.yml", "_l_ukrainian_machine_translation.yml")
            output_file_path = os.path.join(output_dir, output_file_name)

            if os.path.exists(output_file_path) and not overwrite_existing_translation:
                logger.info(f"Skipping {file_name} -> {output_file_name} (already exists)")
                continue
            if not _validate_yaml_file(input_file_path):
                logger.info(f"Skipping {file_name} -> {output_file_name} (invalid YAML)")
                continue

            files_to_translate.append((input_file_path, output_file_path, output_dir))
            if max_translations and len(files_to_translate) >= max_translations:
                break

        if max_translations and len(files_to_translate) >= max_translations:
            break
    logger.info(f"Identified {len(files_to_translate)} files to translate")

    # Create semaphore to limit concurrency
    semaphore = asyncio.Semaphore(max_concurrency)

    # Create tasks for all files
    tasks = [
        translate_file(input_path, output_path, output_dir, translator, semaphore)
        for input_path, output_path, output_dir in files_to_translate
    ]

    # Execute all tasks concurrently
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Count successful translations
    successful = sum(1 for r in results if r is True)
    logger.info(f"Completed: {successful}/{len(files_to_translate)} files translated successfully")


def translate_dir(dir_path: str, translator: Translator, max_translations: int | None = None,
                  overwrite_existing_translation: bool = False, max_concurrency: int = 5):
    """Synchronous wrapper for translate_dir_async."""
    asyncio.run(translate_dir_async(dir_path, translator, max_translations,
                                    overwrite_existing_translation, max_concurrency))


if __name__ == '__main__':
    load_dotenv()
    _translator = GeminiTranslator()
    _source_dir = "../Ukrainian Localization"
    translate_dir(_source_dir, _translator, max_translations=1024, overwrite_existing_translation=False)
