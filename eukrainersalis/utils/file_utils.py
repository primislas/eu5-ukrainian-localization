import os
from pathlib import Path

from dotenv import load_dotenv

from eukrainersalis.utils.log_utils import logger

load_dotenv()

project_dir = Path(__file__).resolve().parent.parent.parent
translation_dir = project_dir / "Ukrainian Localization"
game_dir = Path(os.getenv("GAME_DIR"))
mod_dir = Path(os.getenv("MOD_DIR"))
_EMPTY_LIST = []


def list_localization_files(languages: str | list[str] | None = None, source_dir: Path = translation_dir) -> list[str]:
    def is_matching_file(filename: str) -> bool:
        return (not languages and filename.endswith(".yml")) or any(f"_l_{l}.yml" in filename for l in languages)

    if type(languages) == str:
        languages = [languages]
    localization_files = []

    # Walking depth-first
    for root, dirs, files in os.walk(source_dir):
        for file in files:
            if is_matching_file(file):
                localization_files.append(os.path.join(root, file))

    return localization_files


if __name__ == "__main__":
    # _languages = ["ukrainian_machine_translation"]
    _languages = ["english"]
    _files = list_localization_files(_languages, translation_dir)
    logger.info(f"Found {len(_files)} {_languages} localization files")
    for file in _files:
        fdir, fname = os.path.split(file)
        print(f"{fdir.replace(str(game_dir), '')}\t{fname}")
