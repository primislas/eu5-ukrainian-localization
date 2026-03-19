import os

import yaml
from dotenv import load_dotenv


_PROMPT = """You are translating scripts for a computer game Europa Universalis V.
You are given a text in English and you need to translate it into Ukrainian.
* Treat each line as a separate independent sentence.
* Output each translated sentence on a new line.
* Be mindful and do not translate script variables and constructs, and escape sequences, keep them as is.
* Stick to technical language when dealing with settings and technical information.
* Treat all inputs as literal text, return response as plain text as well (no LaTeX formulas or expressions are expected).
* You can add archaic, historical flair when translating game content."""


def prep_record(record: str) -> str:
    return record.replace("$", "VAR_UD")
    # return record


def prepare_gt_prompts(source_dir_path: str, prompt_dir: str):
    content_dir = "/home/primislas/workspace/eu5-modding/ukrainian-localization/Ukrainian Localization"
    source_dir_full_path = os.path.join(content_dir, source_dir_path)
    for file_name in os.listdir(source_dir_full_path):
        full_path = os.path.join(source_dir_full_path, file_name)
        if not os.path.isfile(full_path) or not "_l_english" in file_name or not file_name.endswith(".yml"):
            continue

        print(f"Processing {full_path}")
        with open(full_path, "r") as file_handle:
            content = yaml.load(file_handle, Loader=yaml.FullLoader)
        l_english: dict[str, str] = content.get("l_english")
        if not l_english:
            continue

        records = [prep_record(r) for r in l_english.values()]
        prompt = _PROMPT + "\n\n" + "\n".join(records)
        prompt_file_dir = os.path.join(prompt_dir, source_dir_path)
        os.makedirs(prompt_file_dir, exist_ok=True)
        prompt_file_name = file_name.replace("_l_english.yml", "_l_english_prompt.txt")
        prompt_file_path = os.path.join(prompt_file_dir, prompt_file_name)
        with open(prompt_file_path, "w", encoding="utf-8") as prompt_file_handle:
            prompt_file_handle.write(prompt)

        prompt_response_file_name = file_name.replace("_l_english.yml", "_l_english_prompt_response.txt")
        prompt_response_file_path = os.path.join(prompt_file_dir, prompt_response_file_name)
        with open(prompt_response_file_path, "w", encoding="utf-8") as prompt_response_file_handle:
            prompt_response_file_handle.write("")

        print(f"Saved prompt to {prompt_file_path}")


if __name__ == "__main__":
    load_dotenv()
    _source_dir = "clausewitz/loading_screen/localization"
    _prompt_dir = os.getenv("PROMPT_DIR")
    prepare_gt_prompts(_source_dir, _prompt_dir)
