import re

from eukrainersalis.utils.file_utils import list_localization_files
from eukrainersalis.utils.translation_utils import Language
from eukrainersalis.utils.yaml_utils import write_eu5_localization_yaml, load_eu5_yaml

_TRADE_GOOD_CASE = {
    "GEN": "Товару",
    "DAT": "Товару",
    "ACC": "Товар",
    "INST": "Товаром",
    "PREP": "Товарі",
}

if __name__ == "__main__":
    _fixed_declaration = 0
    _fixed_files = 0
    _localization_key = Language.RUSSIAN.lang_key
    _goods_regex = r"\$(?P<scope>Goods|GOODS)_GetName(?P<no_tooltip>WithNoTooltip)?_UA_(?P<grammatical_case>GEN|DAT|ACC|INST|PREP)(?P<is_lower_case>_lower)?\$"

    def replace_match(match: re.Match) -> str:
        scope = match.group("scope")
        no_tooltip = match.group("no_tooltip")
        grammatical_case = match.group("grammatical_case")
        is_lower_case = match.group("is_lower_case")

        trade_good_word = _TRADE_GOOD_CASE.get(grammatical_case, "Товар")
        if is_lower_case:
            trade_good_word = trade_good_word.lower()
        replacement = f"{trade_good_word} «[{scope}.GetName{'WithNoTooltip' if no_tooltip else ''}]»"
        return replacement

    for file in list_localization_files("russian_uk_ua_machine_translation"):
        _orig_fixed_declarations = _fixed_declaration
        _content = load_eu5_yaml(file)
        _ucontent = {_localization_key: {}}
        for k, v in _content.get(_localization_key, {}).items():
            uv, replaced_count = re.subn(_goods_regex, replace_match, v)

            if replaced_count == 0:
                _ucontent[_localization_key][k] = v
                continue

            _ucontent[_localization_key][k] = uv
            _fixed_declaration += replaced_count

        if _fixed_declaration > _orig_fixed_declarations:
            write_eu5_localization_yaml(_ucontent, file)
            _fixed_files += 1

    print(f"Fixed {_fixed_declaration} declarations across {_fixed_files} files")
