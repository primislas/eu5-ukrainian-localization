from eukrainersalis.utils.file_utils import estate_ending_file_path

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

def generate_estate_endings():
    # TODO: should automatically insert into estates.txt
    lines = []
    for estate in ESTATES:
        for ending, default in ESTATE_ENDINGS.items():
            lines.append(f"{estate}_{ending} = {{")
            lines.append("  log_loc_errors = no")
            lines.append(f"  parent = {estate}_estate")
            lines.append(f"  suffix = \"_{estate}_estend_{ending}\"")
            # lines.append(f"  text = {{ localization_key = estend_{ending}_def fallback = yes }}")
            # lines.append(f"  if_invalid_loc = \"{default}\"")
            # lines.append(f"  if_invalid_loc = estend_{ending}_def")
            lines.append(f"  if_invalid_loc = return_empty")
            lines.append("}")

    with open(estate_ending_file_path, "w", encoding="utf-8-sig") as f:
        for line in lines:
            f.write(line)
            f.write("\n")
    print(f"{len(lines)} estate ending lines generated to {estate_ending_file_path}")
    print("Estates endings generated successfully.")

if __name__ == "__main__":
    generate_estate_endings()
