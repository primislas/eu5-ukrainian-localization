import os.path
import re

from eukrainersalis.utils.file_utils import list_localization_files
from eukrainersalis.utils.translation_utils import Language
from eukrainersalis.utils.yaml_utils import write_eu5_localization_yaml, load_eu5_yaml


def fix_column_declarations_from_english_source():
    _fixed_files = 0
    _fixed_declaration = 0
    _en_localization_key = Language.ENGLISH.localization_key
    _ru_localization_key = Language.RUSSIAN.localization_key
    col_pattern = r"#col[\s_\[]"

    for en_file in list_localization_files(Language.ENGLISH):
        ua_file = en_file.replace(Language.ENGLISH.localization_key, Language.UK_UA_MACHINE_TRANSLATION.localization_key).replace(Language.ENGLISH, Language.RUSSIAN)
        if not os.path.exists(ua_file):
            print(f"UA file does not exist for: {en_file}")
            continue

        _en_content = load_eu5_yaml(en_file)
        _en_loc = _en_content.get(_en_localization_key, {})

        _ua_content = None
        _ua_loc = None

        for k, v in _en_loc.items():
            if not re.search(col_pattern, v):
                continue

            if not _ua_content:
                _fixed_files += 1
                _ua_content = load_eu5_yaml(ua_file)
                _ua_loc = _ua_content.get(_ru_localization_key, {})

            ua_v = _ua_loc.get(k, "")
            if ua_v:
                if re.search(col_pattern, ua_v):
                    continue
                else:
                    _fixed_declaration += 1
                    _ua_loc[k] = v

        if _ua_loc:
            write_eu5_localization_yaml(_ua_content, ua_file)

    print(f"Fixed {_fixed_declaration} declarations in {_fixed_files} files")


if __name__ == "__main__":
    fix_column_declarations_from_english_source()
