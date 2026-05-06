import os
import shutil
from pathlib import Path

from eukrainersalis.utils.file_utils import game_dir, translation_dir, list_localization_files
from eukrainersalis.utils.translation_utils import Language


def copy_localizations(source_dir: Path, target_dir: Path, languages: list[str]):
    localization_files = list_localization_files(languages, source_dir)
    print(f"Identified {len(localization_files)} localization files")
    localization_files.sort()
    for file in localization_files:
        rel = Path(file).relative_to(source_dir)
        target_file = target_dir / rel
        print(f"Copying {os.path.basename(file)} to {target_file}")
        os.makedirs(os.path.dirname(target_file), exist_ok=True)
        shutil.copy(file, target_file)


if __name__ == "__main__":
    _languages = [Language.ENGLISH, Language.RUSSIAN]
    copy_localizations(game_dir, translation_dir, _languages)
