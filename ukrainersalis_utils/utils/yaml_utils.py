import os

import aiofiles
import re
import yaml

from ukrainersalis_utils.logger import logger
from ukrainersalis_utils.utils.file_utils import list_localization_files


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


def load_eu5_yaml(file_path: str) -> dict:
    with open(file_path, "r") as file_handle:
        return yaml.load(file_handle, Loader=yaml.FullLoader)


def validate_localization_file(file_path: str, language: str = "english") -> bool:
    """Validate a YAML localization file by parsing it and checking for errors."""
    try:
        with open(file_path, "r") as file_handle:
            content = yaml.load(file_handle, Loader=yaml.FullLoader)
        content_key = "l_" + language
        has_english_content = content_key in content and content.get(content_key)
        if not has_english_content:
            logger.debug(f"{file_path} has no {language} localization")
        return has_english_content
    except Exception:
        logger.exception(f"Error parsing {file_path}")
        return False

async def async_load_eu5_yaml(file_path: str) -> dict:
    async with aiofiles.open(file_path, "r") as file_handle:
        content_str = await file_handle.read()
        return yaml.load(content_str, Loader=yaml.FullLoader)

async def async_write_eu5_localization_yaml(data: dict, output_file_path: str) -> int:
    dumped = yaml.dump(
        data,
        Dumper=DoubleQuotedDumper,
        allow_unicode=True,
        sort_keys=False,
        width=float('inf'),
    )
    async with aiofiles.open(output_file_path, "w", encoding="utf-8-sig") as output_file_handle:
        return await output_file_handle.write(dumped.strip())


def fix_concept_declarations(text: str) -> str:
    """
    Detect invalid concept placement and dangling declarations, and move Concept(' back to its location.

    Example input:
    `Дипломатичний статус [Concept('COUNTRY.GetName] НЕ дозволяє створення [alliance', 'CONCEPT_PLACEHOLDER')|e] з [TARGET_COUNTRY.GetName]`
    Example output:
    `Дипломатичний статус [COUNTRY.GetName] НЕ дозволяє створення [Concept('alliance', 'CONCEPT_PLACEHOLDER')|e] з [TARGET_COUNTRY.GetName]`
    """

    # 1. Match [Concept('ANY_TEXT] and group ANY_TEXT
    # 2. Match anything in between (non-greedy, but not crossing another [Concept(')
    # 3. Match [lowercasetext', 'CONCEPT_PLACEHOLDER')|e]
    pattern = r"\[Concept\('([^'\]]+)\]((?:(?!\[Concept\(').)*?)\[([a-z_]+)', 'CONCEPT_PLACEHOLDER'\)\|e\]"

    def replacement(match):
        inner_text = match.group(1)
        between = match.group(2)
        dangling_text = match.group(3)
        return f"[{inner_text}]{between}[Concept('{dangling_text}', 'CONCEPT_PLACEHOLDER')|e]"

    return re.sub(pattern, replacement, text, flags=re.DOTALL)


if __name__ == "__main__":
    fixed_declaration = 0
    unfixed_dangling_concept = 0
    for file in list_localization_files("ukrainian_machine_translation"):
        content = load_eu5_yaml(file)
        for k, v in content.get("l_english", {}).items():
            fixed = fix_concept_declarations(v)
            if v != fixed:
                print(f"{os.path.basename(file)} -> {k}:")
                print(f"\t--- {v}")
                print(f"\t+++ {fixed}")
                fixed_declaration += 1
            else:
                if re.match(r"\[[a-z_]+', 'CONCEPT_PLACEHOLDER'\)\|[eE]\]", v):
                    print(f"{os.path.basename(file)}: {k}: {v}")
                    print(f"\tFound unfixed dangling concept declaration")
                    unfixed_dangling_concept += 1
    print(f"Fixed {fixed_declaration} concept declarations, {unfixed_dangling_concept} unfixed dangling concepts")