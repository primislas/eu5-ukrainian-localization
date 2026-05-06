from eukrainersalis.utils.file_utils import list_localization_files
from eukrainersalis.utils.translation_utils import Language
from eukrainersalis.utils.yaml_utils import write_eu5_localization_yaml, load_eu5_yaml

ending_mappings = {
    "'endlong_fem'": "'endlong_vlaloly'",
    "'end_fem'": "'end_vlaloly'",
    "'endrank_fem'": "'endrank_vlaloly'",
    "'endlong_assya'": "'endlong_vlaloly'",
    "'end_assya'": "'end_vlaloly'",
    "'endrank_assya'": "'endrank_vlaloly'",
    "'endlong_etut'": "'endlong_eut'",
    "'end_etut'": "'end_eut'",
    "'endrank_etut'": "'endrank_eut'",
    "'endlong_etyut'": "'endlong_yeyut'",
    "'end_etyut'": "'end_yeyut'",
    "'endrank_etyut'": "'endrank_yeyut'",
    "'endlong_gegu'": "'endlong_eut'",
    "'end_gegu'": "'end_eut'",
    "'endrank_gegu'": "'endrank_eut'",
    "'endlong_enna'": "'endlong_clean'",
    "'end_enna'": "'end_clean'",
    "'endrank_enna'": "'endrank_clean'",
    "'endlong_itat'": "'endlong_ytyat'",
    "'end_itat'": "'end_ytyat'",
    "'endrank_itat'": "'endrank_ytyat'",
    "'endlong_ityat'": "'endlong_ytyat'",
    "'end_ityat'": "'end_ytyat'",
    "'endrank_ityat'": "'endrank_ytyat'",
    "'predlog_sso'": "'preposition_zzi'",
    "'endlong_predlog_sso'": "'preposition_zzi'",
    "'end_predlog_sso'": "'preposition_zzi'",
    "'predlog_vvo'": "'preposition_uv'",
    "'endlong_predlog_vvo'": "'preposition_uv'", # seems to be a bug in original localization
    "'end_predlog_vvo'": "'preposition_uv'", # seems to be a bug in original localization
    "'endrank_predlog_vvo'": "'preposition_uv'", # seems to be a bug in original localization
    "'predlog_kko'": "'REPLACE_WITH_STATIC_до'",
    "'endlong_predlog_kko'": "'REPLACE_WITH_STATIC_до'",
    "'end_predlog_kko'": "'REPLACE_WITH_STATIC_до'",
    "'endrank_predlog_kko'": "'REPLACE_WITH_STATIC_до'",
    "'predlog_obo'": "'REPLACE_WITH_STATIC_про'",
    "'endlong_predlog_obo'": "'REPLACE_WITH_STATIC_про'",
    "'end_predlog_obo'": "'REPLACE_WITH_STATIC_про'",
    # TODO: end_a? looks like a bug in original localization, look for it in new releases
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
