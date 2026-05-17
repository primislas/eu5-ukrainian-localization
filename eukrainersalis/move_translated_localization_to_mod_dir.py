import os
import shutil
from pathlib import Path

from eukrainersalis.utils.file_utils import list_localization_files, translation_dir, mod_dir, \
    project_mod_dir
from eukrainersalis.utils.yaml_utils import load_eu5_yaml, write_eu5_localization_yaml


def is_replacement_file(file_name: str) -> bool:
    # Original idea was to overwrite ru custom loc to reduce
    # localization engine overload. However, since we know
    # use English as source, l_russian isn't expected to be loaded
    # anyways. Therefore, editing it out.
    # if file_name.startswith("customizable_localization_ru_"):
    #    return False

    # Filenames prefixed with "ua_" are expected to be ukrainersalis
    # modded file, already located where they are supposed to be.
    return not file_name.startswith("ua_")


def _move_localization_file(modded_file: str, output_path: str, relative_input_dir_path: str):
    input_fname = os.path.basename(modded_file)
    output_dir, output_fname = os.path.split(output_path)
    output_dir = output_dir.replace("/russian", "/english")
    output_dir = output_dir.replace("/game/", "/")
    output_fname = output_fname.replace("_uk_ua_machine_translation", "")
    output_fname = output_fname.replace("_l_russian", "_l_english")
    output_path = os.path.join(output_dir, output_fname)
    os.makedirs(output_dir, exist_ok=True)

    content = load_eu5_yaml(modded_file)
    content["l_english"] = content.pop("l_russian")
    write_eu5_localization_yaml(content, output_path)
    relative_output_path = os.path.relpath(output_path, mod_dir)
    print(f"Moved {relative_input_dir_path}/{input_fname}\n   -> {relative_output_path}")


def move_translated_localization_to_mod_dir() -> int:
    tr_root_dirs = os.listdir(translation_dir)
    moved_file_count = 0
    # moving files which are 1-to-1 original equivalents
    for tr_dir in tr_root_dirs:
        source_dir_path = Path(os.path.join(str(translation_dir), tr_dir)).resolve()
        machine_translations = list_localization_files("russian_uk_ua_machine_translation", source_dir=source_dir_path)
        post_edited_translations = list_localization_files("russian_uk_ua_post_edited", source_dir=source_dir_path)
        for mt_file in post_edited_translations + machine_translations:
            moved_file = mt_file
            relative_path = os.path.relpath(mt_file, source_dir_path)
            output_path = os.path.join(mod_dir, relative_path)
            output_file_dir, output_file_name = os.path.split(output_path)
            if is_replacement_file(output_file_name) and not output_file_name.endswith("replace"):
                output_path = os.path.join(output_file_dir, "replace", output_file_name)
            _move_localization_file(moved_file, output_path, relative_path)
            moved_file_count += 1
    return moved_file_count


def move_modded_files_to_mod_dir():
    moved_file_count = 0
    for root, dirs, files in os.walk(project_mod_dir):
        for file in files:
            from_file = os.path.join(root, file)
            rel_path = os.path.relpath(root, project_mod_dir)
            to_dir = os.path.join(mod_dir, rel_path)
            to_file = os.path.join(to_dir, file)
            if file.endswith(".yml"):
                _move_localization_file(from_file, to_file, rel_path)
                moved_file_count += 1
                continue

            os.makedirs(to_dir, exist_ok=True)
            shutil.copy(from_file, to_file)
            moved_file_count += 1
            print(f"Moved {rel_path}/{file}\n   -> {os.path.relpath(to_file, mod_dir)}")
    return moved_file_count


def move_modded_localization_to_mod_dir():
    moved_file_count = 0
    moved_file_count += move_translated_localization_to_mod_dir()
    moved_file_count += move_modded_files_to_mod_dir()

    print(f"Moved {moved_file_count} files")


if __name__ == "__main__":
    move_modded_localization_to_mod_dir()
