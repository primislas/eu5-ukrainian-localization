import os
import shutil
from pathlib import Path, PurePosixPath

from eukrainersalis.utils.file_utils import list_localization_files, mod_dir, \
    mod_compatibility_dir, rasf_local_game_mod_dir
from eukrainersalis.utils.log_utils import simple_logger as logger


def _move_localization_file(modded_file: str, output_path: str, relative_input_dir_path: str):
    input_fname = os.path.basename(modded_file)
    output_dir, output_fname = os.path.split(output_path)
    output_dir = output_dir.replace("/russian", "/english")
    output_dir = output_dir.replace("/game/", "/")
    output_fname = output_fname.replace("_uk_ua_machine_translation", "")
    output_fname = output_fname.replace("_l_russian", "_l_english")
    output_path = os.path.join(output_dir, output_fname)
    os.makedirs(output_dir, exist_ok=True)

    shutil.copy(modded_file, output_path)
    relative_output_path = os.path.relpath(output_path, mod_dir)
    logger.info(f"Moved {relative_input_dir_path}/{input_fname}\n   -> {relative_output_path}")


def move_translated_localization_to_mod_dir() -> int:
    mod_compat_dir = mod_compatibility_dir / "ruthenia_and_steppe_fix" / "3608237308"
    tr_root_dirs = os.listdir(mod_compat_dir)
    moved_file_count = 0
    # moving files which are 1-to-1 original equivalents
    for tr_dir in tr_root_dirs:
        source_dir_path = Path(os.path.join(str(mod_compat_dir), tr_dir)).resolve()
        machine_translations = list_localization_files("russian_uk_ua_machine_translation", source_dir=source_dir_path)
        post_edited_translations = list_localization_files("russian_uk_ua_post_edited", source_dir=source_dir_path)
        for mt_file in post_edited_translations + machine_translations:
            moved_file = mt_file
            relative_path = os.path.relpath(mt_file, mod_compat_dir)
            if relative_path.startswith("dlc/"):
                # It appears the game has special handling for dlc folder.
                # Its layout usually is dlc/DNNN/main_menu, where
                # DNNN is the dlc id, and main_menu corresponds to
                # standard game/main_menu folder.
                relative_path = PurePosixPath(*PurePosixPath(relative_path).parts[2:]).as_posix()
            output_path = rasf_local_game_mod_dir / relative_path
            output_file_dir, output_file_name = os.path.split(output_path)
            output_path = os.path.join(output_file_dir, "380_" + output_file_name)
            _move_localization_file(moved_file, output_path, relative_path)
            moved_file_count += 1

    metadata_file_path = mod_compat_dir / ".metadata" / "metadata-risyi.json"
    thumbnail_file_path = mod_compat_dir / ".metadata" / "thumbnail-risyi.png"
    target_metadata_dir = rasf_local_game_mod_dir / ".metadata"
    os.makedirs(target_metadata_dir, exist_ok=True)
    for f in [metadata_file_path, thumbnail_file_path]:
        fname = os.path.basename(f)
        target_fname = fname.replace("-risyi", "")
        target_file_path = target_metadata_dir / target_fname
        shutil.copy(f, target_file_path)
        moved_file_count += 1

    return moved_file_count


def move_mod_compat_localization_to_mod_dir():
    moved_file_count = 0
    moved_file_count += move_translated_localization_to_mod_dir()

    logger.info(f"Moved {moved_file_count} files")


if __name__ == "__main__":
    move_mod_compat_localization_to_mod_dir()
