

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
    for estate in ESTATES:
        for ending, default in ESTATE_ENDINGS.items():
            print(f"{estate}_{ending} = {{")
            print("  log_loc_errors = no")
            print(f"  parent = {estate}_estate")
            print(f"  suffix = \"_{estate}_estend_{ending}\"")
            # print(f"  text = {{ localization_key = estend_{ending}_def fallback = yes }}")
            # print(f"  if_invalid_loc = \"{default}\"")
            print(f"  if_invalid_loc = estend_{ending}_def")
            # print(f"  if_invalid_loc = return_empty")
            print("}")


if __name__ == "__main__":
    generate_estate_endings()
