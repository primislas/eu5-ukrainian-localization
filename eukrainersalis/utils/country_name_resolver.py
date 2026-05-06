from eukrainersalis.utils import file_utils
from eukrainersalis.utils.log_utils import logger
from eukrainersalis.utils.yaml_utils import load_eu5_yaml


_MAPPINGS = {
    "SMC": "Струмиця",
}


def resolve_country_names(source_language: str):
    language_key = f"l_{source_language}"
    loc_dir = file_utils.translation_dir / "game" / "main_menu" / "localization" / source_language
    country_names_file = loc_dir / f"country_names_{language_key}_uk_ua_machine_translation.yml"
    formables_file = loc_dir / f"formable_countries_{language_key}_uk_ua_machine_translation.yml"

    country_names = load_eu5_yaml(country_names_file).get(f"l_{source_language}", {})
    formables = load_eu5_yaml(formables_file).get(f"l_{source_language}", {})

    countries = {}
    for k,v in {**country_names, **formables}.items():
        if len(k) == 3:
            if v.startswith("$") and v.endswith("$"):
                v = v[1:-1]
                if v in country_names:
                    countries[k] = country_names[v]
                elif v in formables:
                    countries[k] = formables[v]
                elif v in _MAPPINGS:
                    countries[k] = _MAPPINGS[v]
                else:
                    logger.warning(f"Could not resolve country name for {k}: {v}")
            else:
                countries[k] = v

    logger.info(f"Resolved {len(countries)} country names")
    for k,v in countries.items():
        print(f"{k},{v}")



if __name__ == "__main__":
    resolve_country_names("russian")