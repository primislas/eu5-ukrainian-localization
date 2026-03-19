import os
import shutil
from pathlib import Path


def _identify_localization_files(remaining_dirs: list[Path], languages: list[str], localization_files: list[Path]) -> list[Path]:
    localization_suffixes = [f"_l_{language}.yml" for language in languages]
    if not remaining_dirs:
        return localization_files

    unprocessed_dirs = []
    for directory in remaining_dirs:
        for file in os.listdir(directory):
            if os.path.isfile(directory / file):
                if any([file.endswith(suffix) for suffix in localization_suffixes]):
                    localization_files.append(directory / file)
            else:
                unprocessed_dirs.append(directory / file)
    return _identify_localization_files(unprocessed_dirs, languages, localization_files)

# src_root = Path("/my/root/path").resolve()
# full_path = Path("/my/root/dir/sub/dir/content/file.txt").resolve()
# target_root = Path("/some/target/dir").resolve()
#
# # If you are sure full_path is under src_root:
# try:
#     rel = full_path.relative_to(src_root)   # raises ValueError if not under src_root
# except ValueError:
#     raise RuntimeError(f"{full_path} is not inside source root {src_root}")
#
# target_path = target_root / rel
# print(target_path)

def copy_localizations(source_dir: Path, target_dir: Path, languages: list[str]):
    localization_files = _identify_localization_files([source_dir], languages, [])
    print(f"Identified {len(localization_files)} localization files")
    localization_files.sort()
    for file in localization_files:
        rel = file.relative_to(source_dir)
        target_file = target_dir / rel
        print(f"Copying {os.path.basename(file)} to {target_file}")
        os.makedirs(os.path.dirname(target_file), exist_ok=True)
        shutil.copy(file, target_file)


if __name__ == "__main__":
    _game_dir = Path("/home/primislas/.steam/debian-installation/steamapps/common/Europa Universalis V")
    # _mod_dir = Path("/home/primislas/.steam/debian-installation/steamapps/compatdata/3450310/pfx/drive_c/users/steamuser/Documents/Paradox Interactive/Europa Universalis V/mod/Ukrainian Localization")
    _mod_dir = Path("/home/primislas/workspace/eu5-modding/ukrainian-localization/Ukrainian Localization/game/main_menu/localization/english/events/disasters")
    _languages = ["english", "russian"]

    copy_localizations(_game_dir, _mod_dir, _languages)
