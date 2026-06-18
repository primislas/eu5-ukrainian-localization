import json
import re

from eukrainersalis.utils.estate_ending_generator import get_estate_names
from eukrainersalis.utils.file_utils import estate_grammatical_case_output_file_path, \
    estate_grammatical_case_config_file_path
from eukrainersalis.utils.translation_utils import Language
from eukrainersalis.utils.yaml_utils import load_eu5_yaml, write_eu5_localization_yaml

ESTATE_KEY_MAPPINGS = {
    "$qizilbash$": "Кизилбаші",
    "[ROOT.GetCountry.GetCulture.Custom('character_title_prefix_captain_plural')]": "Капітани"
}


def extract_estate_cases_from_localization_file(localization_file_path):
    localization_data = load_eu5_yaml(localization_file_path).get(Language.RUSSIAN.localization_key, {})
    estate_cases = []
    for key, value in localization_data.items():
        if key.startswith("ESTATE") or key.startswith("Estate"):
            estate_cases.extend(extract_estate_cases_from_single_declaration(key, value))

    merged_estate_cases = {}
    for estate_case in estate_cases:
        nom_val = estate_case["NOM"]
        if nom_val in merged_estate_cases:
            merged_estate_cases[nom_val].update(estate_case)
        else:
            merged_estate_cases[nom_val] = estate_case

    normalized_estate_cases = {}
    for nom_val, estate_case in merged_estate_cases.items():
        if not all(case_key in estate_case for case_key in ["NOM", "GEN", "DAT", "ACC", "INST", "PREP"]):
            print(f"Warning: Missing case for {nom_val}: {estate_case}")
        normalized_estate_cases[nom_val] = {case_key: estate_case.get(case_key, estate_case.get("NOM")) for case_key in ["NOM", "GEN", "DAT", "ACC", "INST", "PREP"]}

    return list(normalized_estate_cases.values())


def extract_estate_cases_from_single_declaration(localization_key, localization_value):
    # Extract estate_form (starts with ESTATE or Estate)
    estate_form = ""
    if localization_key.startswith("ESTATE"):
        estate_form = "ESTATE"
    elif localization_key.startswith("Estate"):
        estate_form = "Estate"

    # Extract grammatical case (GEN, DAT, ACC, INST, PREP)
    cases = ["GEN", "DAT", "ACC", "INST", "PREP"]
    grammatical_case = ""
    parts = localization_key.split("_")
    for part in parts:
        if part in cases:
            grammatical_case = part
            break

    # Value can have multiple "AddTextIf" declarations
    # [AddTextIf(EqualTo_string('Знать', ESTATE.GetNameWithNoTooltip), 'Знаті')]
    # Regex to extract strings between single quotes inside AddTextIf
    pattern = r"\[AddTextIf\(EqualTo_string\('([^']*)', [^)]*\), '([^']*)'\)\]"
    matches = re.findall(pattern, localization_value)
    if not matches:
        return []

    results = []
    for nom_val, case_val in matches:
        obj = {
            "NOM": nom_val,
            grammatical_case: case_val.capitalize()
        }
        results.append(obj)

    return results


def print_estate_cases_from_output_file():
    """Useful to rebuild estate_grammatical_cases.json"""
    estates = extract_estate_cases_from_localization_file(estate_grammatical_case_output_file_path)
    print(f"Found {len(estates)} estates:")
    print(json.dumps(estates, indent=2, sort_keys=False, ensure_ascii=False))


def detect_estates_without_cases():
    estates = get_estate_names()
    with open(estate_grammatical_case_config_file_path, "r", encoding="utf-8") as estate_conf_file:
        estate_cases = json.load(estate_conf_file)
    estate_declarations = set(ESTATE_KEY_MAPPINGS.get(e, e) for e in estates)
    nom_estates = set(estate_case["NOM"] for estate_case in estate_cases)
    estates_without_cases = []
    for estate in estates:
        if estate not in nom_estates and ESTATE_KEY_MAPPINGS.get(estate) not in nom_estates:
            estates_without_cases.append(ESTATE_KEY_MAPPINGS.get(estate, estate))

    print(f"Detected {len(estates_without_cases)} estates without cases:")
    for estate in estates_without_cases:
        print(estate)

    print()
    print(f"Estate templates:")
    templates = [{case_key: estate for case_key in ["NOM", "GEN", "DAT", "ACC", "INST", "PREP"]} for estate in estates_without_cases]
    print(json.dumps(templates, indent=2, sort_keys=False, ensure_ascii=False))

    redundant_case_declarations = list(estate_declarations - nom_estates)
    print(f"Redundant estate case declarations: {redundant_case_declarations}")


def generate_estate_cases_localization():
    """Generates localization keys for estates based on configuration."""
    estate_cases = []
    with open(estate_grammatical_case_config_file_path, "r", encoding="utf-8") as estate_conf_file:
        estate_cases = json.load(estate_conf_file)

    localization = {}
    for estate_scope in ["ESTATE", "Estate"]:
        for grammatical_case in ["GEN", "DAT", "ACC", "INST", "PREP"]:
            for writing_case in ["", "_lower"]:
                loc_key = f"{estate_scope}_GetNameWithNoTooltip_UA_{grammatical_case}{writing_case}"
                estate_locs = []
                l_transformer = "|l" if writing_case == "_lower" else ""
                for estate in estate_cases:
                    estate_case = estate[grammatical_case]
                    estate_case = estate_case if writing_case != "_lower" else estate_case.lower()
                    estate_case_declaration = f"[AddTextIf(EqualTo_string('{estate["NOM"]}', {estate_scope}.GetNameWithNoTooltip), '{estate_case}'){l_transformer}]"
                    estate_locs.append(estate_case_declaration)
                localization[loc_key] = "".join(estate_locs)

    output = load_eu5_yaml(estate_grammatical_case_output_file_path)
    output_loc = output.get(Language.RUSSIAN.localization_key, {})
    output_loc.update(localization)
    write_eu5_localization_yaml(output, estate_grammatical_case_output_file_path)

def main():
    # print_estate_cases_from_output_file()
    # detect_estates_without_cases()
    generate_estate_cases_localization()


if __name__ == "__main__":
    main()
