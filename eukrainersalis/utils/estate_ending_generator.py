from eukrainersalis.utils.file_utils import estate_ending_custom_loc_file_path, estate_localization_file_path, \
    customized_estate_ending_file_path, generated_estate_ending_file_path, modded_estate_localization_file_path
from eukrainersalis.utils.translation_utils import Language
from eukrainersalis.utils.yaml_utils import load_eu5_yaml, write_eu5_localization_yaml

ESTATES = ["crown", "clergy", "nobles", "burghers", "peasants", "tribes", "cossacks"]

# endings and default values
ESTATE_ENDINGS = {
    "yeyut": "ють",
    "vlaloly": "ли",
    "yiaei": "і",
    "eut": "уть",
    "aei": "і",
    "ytyat": "ять",
    "ytat": "ать",
    "ytlyat": "лять",
    "yityat": "ять",
    "yetsayutsa": "ються",
    "etsautsa": "уться",
    "ihohlaloly": "огли",
    "ohooyiyh": "их",
    "iyyayei": "і",
    "essyasesi": "сі",
    "eyyaei": "і",
    "ymoyuymy": "ими",
    "ovlaloly": "ли",
    "ennanoni": "ні",
}


def get_estate_names():
    estate_names = set()
    for declaration_file in [estate_localization_file_path, modded_estate_localization_file_path]:
        estate_declaration = load_eu5_yaml(declaration_file).get("l_russian", {})
        for k in estate_declaration.keys():
            elems = k.split("_")
            if len(elems) == 2 and elems[1] == "estate":
                estate_names.add(k)
        for k in estate_declaration.keys():
            if any(k.startswith(estate_name) for estate_name in estate_names):
                if not k.endswith("_desc"):
                    estate_names.add(k)
    estate_names = sorted(list(estate_names))
    return estate_names


def generate_loc_estate_endings():
    """Generates estate ending localization, based on the customized ending localization,
    and applying default values for the rest."""
    estate_names = get_estate_names()
    customized_endings = load_eu5_yaml(customized_estate_ending_file_path).get(Language.RUSSIAN.localization_key, {})

    current_ending_key = ""
    current_ending_key_default_value = ""
    output = {}
    for k, v in customized_endings.items():
        is_def = k.endswith("_def")
        if is_def or "_GetEnd_" in k:
            if current_ending_key != "":
                for estate in estate_names:
                    estate_prefix = estate.split("_")[0]
                    estate_ending = f"{estate}_{estate_prefix}_{current_ending_key}"
                    if estate_ending not in output:
                        output[estate_ending] = current_ending_key_default_value
            current_ending_key = k.replace("_def", "") if is_def else ""
            current_ending_key_default_value = v if is_def else ""
        output[k] = v
    output_loc = {Language.RUSSIAN.localization_key: output}
    write_eu5_localization_yaml(output_loc, generated_estate_ending_file_path)
    print(f"{len(output)} estate endings generated to {generated_estate_ending_file_path}")


def get_custom_estate_endings():
    return load_eu5_yaml(estate_ending_custom_loc_file_path).get("l_russian", {})


def generate_custom_loc_script_estate_endings():
    # TODO: should automatically insert into estates.txt
    lines = []
    for estate in ESTATES:
        for ending, default in ESTATE_ENDINGS.items():
            lines.append(f"{estate}_{ending} = {{")
            lines.append("  log_loc_errors = no")
            lines.append(f"  parent = {estate}_estate")
            lines.append(f"  suffix = \"_{estate}_estend_{ending}\"")
            lines.append(f"  if_invalid_loc = return_empty")
            lines.append("}")

    with open(estate_ending_custom_loc_file_path, "w", encoding="utf-8-sig") as f:
        for line in lines:
            f.write(line)
            f.write("\n")
    print(f"{len(lines)} estate ending script lines generated to {estate_ending_custom_loc_file_path}")


if __name__ == "__main__":
    generate_custom_loc_script_estate_endings()
    generate_loc_estate_endings()
