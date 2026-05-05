from eukrainersalis.utils.file_utils import list_localization_files
from eukrainersalis.utils.translation_utils import Language
from eukrainersalis.utils.yaml_utils import write_eu5_localization_yaml, load_eu5_yaml

ending_mappings = {
    "'endlong_fem'": "'endlong_v_la'",
    "'endlong_etut'": "'endlong_eut'",
    "'endlong_etyut'": "'endlong_yeyut'",
}

if __name__ == "__main__":
    # Keeping ending patching separate, to be able to detect them at a glance
    # with more ease, and to manually patching, as they usually end up
    # being pretty messy.

    _fixed_declaration = 0
    _unfixed_dangling_concept = 0
    _localization_key = Language.RUSSIAN.localization_key
    for file in list_localization_files("russian_uk_ua_machine_translation"):
        _content = load_eu5_yaml(file)
        for k, v in _content.get(_localization_key, {}).items():
            for ek, ev in ending_mappings.items():
                if ek in v:
                    u = v
                    u = u.replace(ek, ev)
                    _content[_localization_key][k] = u
                    if u != v:
                        _fixed_declaration += 1

        write_eu5_localization_yaml(_content, file)
    print(f"Fixed {_fixed_declaration} declarations")
