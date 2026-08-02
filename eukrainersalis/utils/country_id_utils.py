import re

_save_game_file = "/home/primislas/.steam/debian-installation/steamapps/compatdata/3450310/pfx/drive_c/users/steamuser/Documents/Paradox Interactive/Europa Universalis V/save games/autosave_b55c634a-7e92-4e35-ab7b-b17f3c51477a_1.eu5"
_declaration_start_regex = re.compile(r"(\d+)=\{")
_original_tag_regex = re.compile(r'original_tag="([A-Z]{3})"')

def extract_tag_ids_from_save_game_file(save_game_file):
    tag_ids = {}

    with open(save_game_file, encoding="utf-8") as f:
        current_obj_id = 0
        for line in f:
            # TODO: test if regex matches and extract obj ID capturing group
            if match := _declaration_start_regex.search(line):
               current_obj_id = int(match.group(1))
            if match := _original_tag_regex.search(line):
                tag = match.group(1)
                tag_ids[current_obj_id] = tag

    for tag_id in sorted(tag_ids.keys()):
        print(f"  {tag_ids[tag_id]}_UA_CL_tt: \"{tag_id}\"")


if __name__ == "__main__":
    extract_tag_ids_from_save_game_file(_save_game_file)
