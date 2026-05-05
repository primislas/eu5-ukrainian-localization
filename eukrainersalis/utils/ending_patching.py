from eukrainersalis.utils.file_utils import list_localization_files
from eukrainersalis.utils.translation_utils import Language
from eukrainersalis.utils.yaml_utils import write_eu5_localization_yaml, load_eu5_yaml

ending_mappings = {
    "'endlong_fem'": "'endlong_vlaloly'",
    "'end_fem'": "'end_vlaloly'",
    "'endlong_etut'": "'endlong_eut'",
    "'endlong_etyut'": "'endlong_yeyut'",
    "'endlong_gegu'": "'endlong_eut'",
    "'end_gegu'": "'end_eut'",
    "'endlong_enna'": "'endlong_clean'",
    "'end_enna'": "'end_clean'",
    "'predlog_sso'": "'preposition_zzi'",
    "'endlong_predlog_sso'": "'preposition_zzi'",
    "'end_predlog_sso'": "'preposition_zzi'",
    "'predlog_vvo'": "'preposition_uv'",
    "'endlong_predlog_vvo'": "'preposition_uv'", # seems to be a bug in original localization
    "'end_predlog_vvo'": "'preposition_uv'", # seems to be a bug in original localization
    "'predlog_kko'": "'REPLACE_WITH_STATIC_до'",
    "'predlog_obo'": "'REPLACE_WITH_STATIC_про'",
    # TODO: end_a?
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
