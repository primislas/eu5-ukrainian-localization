import os

import yaml
from dotenv import load_dotenv


_PROMPT = """You are translating scripts for a computer game Europa Universalis V.
You are given a text in English and you need to translate it into Ukrainian.
* Treat each line as a separate independent sentence.
* Output each translated sentence on a new line.
* Be mindful and do not translate script variables and constructs, and escape sequences, keep them as is.
* Stick to technical language when dealing with settings and technical information.
* You can add archaic, historical flair when translating game content."""


def parse_record(record: str) -> str:
    return record.replace("VAR_UD", "$")


def insert_results(prompt_dir: str, source_dir_path: str):
    content_dir = "/home/primislas/workspace/eu5-modding/ukrainian-localization/Ukrainian Localization"
    source_dir_full_path = os.path.join(content_dir, source_dir_path)
    for game_file_name in os.listdir(source_dir_full_path):
        game_file_full_path = os.path.join(source_dir_full_path, game_file_name)
        if not os.path.isfile(game_file_full_path) or not "_l_english" in game_file_name or not game_file_name.endswith(".yml"):
            continue

        with open(game_file_full_path, "r") as file_handle:
            yaml_content = yaml.load(file_handle, Loader=yaml.FullLoader)
        l_english: dict[str, str] = yaml_content.get("l_english")
        if not l_english:
            continue

        prompt_file_dir = os.path.join(prompt_dir, source_dir_path)
        os.makedirs(prompt_file_dir, exist_ok=True)
        prompt_response_file_name = game_file_name.replace("_l_english.yml", "_l_english_prompt_response.txt")
        prompt_response_file_path = os.path.join(prompt_file_dir, prompt_response_file_name)
        if not os.path.exists(prompt_response_file_path):
            continue

        print(f"Processing {game_file_full_path}")
        with open(prompt_response_file_path, "r", encoding="utf-8") as prompt_response_file_handle:
            response = prompt_response_file_handle.read()
        response_lines = [parse_record(r) for r in response.split("\n")]

        if not len(l_english) == len(response_lines):
            print(f"Error: {game_file_full_path} has {len(l_english)} records, but {len(response_lines)} lines in the response file")
            continue

        for key, value in zip(l_english.keys(), response_lines):
            l_english[key] = value

        with open(game_file_full_path, "w", encoding="utf-8") as file_handle:
            yaml.dump(yaml_content, file_handle, allow_unicode=True, sort_keys=False)

        print(f"Saved results to {game_file_full_path}")


if __name__ == "__main__":
    load_dotenv()
    _prompt_dir = os.getenv("PROMPT_DIR")
    _source_dir = "clausewitz/loading_screen/localization"
    insert_results(_prompt_dir, _source_dir)
