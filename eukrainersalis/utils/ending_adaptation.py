from eukrainersalis.utils.file_utils import translation_dir
from eukrainersalis.utils.log_utils import logger
from eukrainersalis.utils.translation_utils import Language
from eukrainersalis.utils.yaml_utils import write_eu5_localization_yaml, load_eu5_yaml

ending_configs = [
    {
        "from": "fem",
        "to": "vlaloly",
        "value_mappings": {
            "": "в",
            "а": "ла",
            "о": "ло",
            "и": "ли",
        }
    },
    {
        "from": "enna",
        "to": "clean",
        "value_mappings": {
            "ен": "ий",
            "на": "а",
            "ена": "а",
            "но": "о",
            "ено": "о",
            "ны": "і",
            "ены": "і",
        }
    },
    {
        "from": "etut",
        "to": "eut",
        "value_mappings": {
            "ет": "е",
            "ут": "уть",
        }
    },
    {
        "from": "etyut",
        "to": "yeyut",
        "value_mappings": {
            "ет": "є",
            "ют": "ють",
        }
    },
    {
        "from": "etyut",
        "to": "yeyu",
        "value_mappings": {
            "ет": "є",
            "ют": "ю",
        }
    },
    {
        "from": "etyut",
        "to": "ytyat",
        "value_mappings": {
            "ет": "ить",
            "ют": "ять",
        }
    },
    {
        "from": "etyut",
        "to": "ytat",
        "value_mappings": {
            "ет": "ить",
            "ют": "ать",
        }
    },
    {
        "from": "etyut",
        "to": "ytlyat",
        "value_mappings": {
            "ет": "ить",
            "ют": "лять",
        }
    },
    {
        "from": "etyut",
        "to": "yityat",
        "value_mappings": {
            "ет": "їть",
            "ют": "ять",
        }
    },
    {
        "from": "predlog_sso",
        "to": "preposition_zzi",
        "value_mappings": {
            "с": "з",
            "c": "з",
            "со": "зі",
            "co": "зі",
        }
    },
    {
        "from": "predlog_vvo",
        "to": "preposition_uv",
        "value_mappings": {
            "в": "в",
            "вo": "у",
            "во": "у",
            "у": "у",
        }
    },
]

def adapt_endings(source_language: Language = Language.RUSSIAN, target_language: Language = Language.RUSSIAN):
    custom_ending_file_path = translation_dir / "game" / "main_menu" / "localization" / source_language / f"customizable_localization_ru_end_{source_language.localization_key}.yml"
    content = load_eu5_yaml(custom_ending_file_path)
    localization = content.get(source_language.localization_key, {})
    logger.info(f"{len(localization)} keys to adapt")

    for config in ending_configs:
        from_tag = config["from"]
        to_tag = config["to"]
        value_mappings = config["value_mappings"]
        output_file_path = translation_dir / "game" / "main_menu" / "localization" / target_language / f"customizable_localization_ua_end_{to_tag}_l_russian_uk_ua_machine_translation.yml"

        tech_localization = {}
        rank_localization = {}
        end_localization = {}
        misc_localization = {}
        for key, value in localization.items():
            if f"_{from_tag}" in key:
                new_key = key.replace(f"_{from_tag}", f"_{to_tag}").replace("_ru_", "_ua_").replace("_RU_", "_UA_")
                if "default" in key or "_def" in key or "def_" in key:
                    loc = tech_localization
                else:
                    loc = rank_localization if "rank" in key else end_localization if "end" in key else misc_localization
                if value in value_mappings:
                    loc[new_key] = value_mappings.get(value)
                else:
                    logger.warning(f"Mapping missing for {key} -> {value}")
                    loc[new_key] = value
        target_localization = {
            **tech_localization,
            **dict(sorted(rank_localization.items())),
            **dict(sorted(end_localization.items())),
            **dict(sorted(misc_localization.items())),
        }
        tag_content = {target_language.localization_key: target_localization}
        write_eu5_localization_yaml(tag_content, output_file_path)
        logger.info(f"Adapted {len(target_localization)} keys to {to_tag} from {from_tag} in {output_file_path}")


if __name__ == "__main__":
    adapt_endings()
