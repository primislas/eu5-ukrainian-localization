import os
import re

from eukrainersalis.utils.file_utils import list_localization_files
from eukrainersalis.utils.log_utils import logger
from eukrainersalis.utils.translation_utils import Language
from eukrainersalis.utils.yaml_utils import load_eu5_yaml, write_eu5_localization_yaml

_HARDCODED_TOOLTIP_REGEX = r"TOOLTIP:(?P<tooltip_type>DYNASTY|CULTURE|RELIGION|INTERNATIONAL_ORGANIZATION),(?P<ref_id>\$(?P<key>[a-zA-Z0-9_]+)_tt\$),X"
_HARDCODED_TOOLTIP_PATTERN: re.Pattern = re.compile(_HARDCODED_TOOLTIP_REGEX)


GETTER_BY_TOOLTIP_TYPE = {
    "CULTURE": "GetCultureByKey",
    "DYNASTY": "GetDynasty",
    "RELIGION": "GetReligionByKey",
    "INTERNATIONAL_ORGANIZATION": "GetUniqueInternationalOrganization",
}


def patch_hardcoded_tooltip_ids():

    keys_by_type = {k: set() for k in GETTER_BY_TOOLTIP_TYPE.keys()}

    def _replace_match(match: re.Match) -> str:
        tooltip_type = match.group("tooltip_type")
        key = match.group("key")
        keys_by_type[tooltip_type].add(key)

        getter = GETTER_BY_TOOLTIP_TYPE[tooltip_type]
        replacement = f"TOOLTIP:{tooltip_type},[{getter}('{key}').GetID],X"
        return replacement

    _fixed_files = 0
    _fixed_declarations = 0
    _localization_key = Language.RUSSIAN.lang_key
    for file in list_localization_files(Language.UK_UA_MACHINE_TRANSLATION):
        _orig_fixed_declarations = _fixed_declarations
        _content = load_eu5_yaml(file)
        _ucontent = {_localization_key: {}}
        for k, v in _content.get(_localization_key, {}).items():
            uv, replaced_count = re.subn(_HARDCODED_TOOLTIP_PATTERN, _replace_match, v)

            if replaced_count == 0:
                _ucontent[_localization_key][k] = v
                continue

            _ucontent[_localization_key][k] = uv
            _fixed_declarations += replaced_count

        if _fixed_declarations > _orig_fixed_declarations:
            logger.info(f"Patched {_fixed_declarations - _orig_fixed_declarations} declarations in: {os.path.basename(file)}")
            write_eu5_localization_yaml(_ucontent, file)
            _fixed_files += 1

    for tooltip_type, keys in keys_by_type.items():
        logger.info(f"Detected {len(keys)} keys of type {tooltip_type}: {sorted(keys)}")
    logger.info(f"Fixed {_fixed_declarations} tooltip ids in {_fixed_files} files")


if __name__ == "__main__":
    patch_hardcoded_tooltip_ids()
