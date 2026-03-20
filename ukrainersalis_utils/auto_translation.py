import os
import re
from pathlib import Path
from queue import Queue

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


def translate_dir(dir_path: str, translator: Translator, max_translations: int | None = None,
                  overwrite_existing_translation: bool = False):
    remaining_dirs = Queue()
    remaining_dirs.put(Path(dir_path))

    translated_files = 0
    while not remaining_dirs.empty():
        current_dir = remaining_dirs.get()
        for file_name in os.listdir(current_dir):
            input_file_path = os.path.join(current_dir, file_name)

            if os.path.isdir(input_file_path):
                remaining_dirs.put(Path(input_file_path))
                continue

            if not os.path.isfile(
                    os.path.join(current_dir, file_name)) or not "_l_english" in file_name or not file_name.endswith(
                    ".yml"):
                continue

            output_dir = str(current_dir).replace("/english", "/ukrainian")
            output_file_name = file_name.replace("_l_english.yml", "_l_ukrainian_machine_translation.yml")
            output_file_path = os.path.join(output_dir, output_file_name)
            if os.path.exists(output_file_path) and not overwrite_existing_translation:
                logger.info(f"Skipping {file_name} -> {output_file_name} (already exists)")
                continue

            try:
                with open(os.path.join(current_dir, file_name), "r") as file_handle:
                    content = yaml.load(file_handle, Loader=yaml.FullLoader)
                l_english = content.get("l_english")
                if not l_english:
                    logger.info(f"Skipping {file_name} -> {output_file_name} (no l_english key)")
                    continue

                lines = "\n".join([translation_preprocessing(l) for l in l_english.values()])
                logger.info(f"Translating {input_file_path}")
                translation = translator.translate(lines).splitlines()
                for key, value in zip(l_english.keys(), translation):
                    translated_value = translation_postprocessing(value)
                    if translated_value == "" and value != "":
                        logger.warning(f"Empty translation for {key} in {file_name}, potentially a translation glitch")
                        translated_value = "POSTEDIT_EMPTY_TRANSLATION"
                    l_english[key] = translated_value

                if not os.path.exists(output_dir):
                    os.makedirs(output_dir)
                with open(output_file_path, "w") as output_file_handle:
                    dumped = yaml.dump(
                        content,
                        Dumper=DoubleQuotedDumper,
                        allow_unicode=True,
                        sort_keys=False,
                        width=float('inf'),
                    )
                    output_file_handle.write(dumped.strip())
                logger.info(f"Translated {file_name} -> {output_file_name}")
                translated_files += 1
                if max_translations and translated_files >= max_translations:
                    logger.info(f"Reached max translations ({max_translations})")
                    return
            except Exception as e:
                logger.exception(f"Error processing {file_name}: {e}")

        logger.info(f"Processed {current_dir}")


if __name__ == '__main__':
    load_dotenv()
    _translator = GeminiTranslator()
    _source_dir = "../Ukrainian Localization"
    translate_dir(_source_dir, _translator, max_translations=20, overwrite_existing_translation=False)
