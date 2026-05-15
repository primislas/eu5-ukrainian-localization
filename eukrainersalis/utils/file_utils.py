import os
from pathlib import Path

from dotenv import load_dotenv

from eukrainersalis.utils.log_utils import logger
from eukrainersalis.utils.translation_utils import Language

load_dotenv()

project_dir = Path(__file__).resolve().parent.parent.parent
project_mod_dir = project_dir / "mod"
translation_dir = project_dir / "Ukrainian Localization"
custom_localization_translation_dir_path = translation_dir / "game" / "in_game" / "common" / "customizable_localization"
custom_localization_mod_dir_path = project_mod_dir / "in_game" / "common" / "customizable_localization"

game_dir = Path(os.getenv("GAME_DIR", "./"))
mod_dir = Path(os.getenv("MOD_DIR", "./"))

custom_localization_game_dir_path = game_dir / "game" / "in_game" / "common" / "customizable_localization"


_EMPTY_LIST = []


def list_localization_files(languages: Language | str | list[Language | str] | None = None, source_dir: Path = translation_dir) -> list[str]:
    if isinstance(languages, (str, Language)):
        languages = [languages]
    localization_files = []
    def is_matching_file(filename: str) -> bool:
        return (not languages and filename.endswith(".yml")) or any(f"_l_{l}.yml" in filename for l in languages)

    # Walking depth-first
    for root, dirs, files in os.walk(source_dir):
        for file in files:
            if is_matching_file(file):
                localization_files.append(os.path.join(root, file))

    return localization_files


def list_translation_files(languages: Language | str | list[Language | str] | None = None, source_dir: Path = translation_dir) -> list[str]:
    
    return list_localization_files(languages, source_dir)


if __name__ == "__main__":
    # _languages = ["ukrainian_machine_translation"]
    _languages = [Language.ENGLISH]
    _files = list_localization_files(_languages, translation_dir)
    logger.info(f"Found {len(_files)} {_languages} localization files")
    for file in _files:
        fdir, fname = os.path.split(file)
        print(f"{fdir.replace(str(game_dir), '')}\t{fname}")
