import os
import shutil
from pathlib import Path

from eukrainersalis.utils.file_utils import list_localization_files, translation_dir, mod_dir, \
    project_mod_dir
from eukrainersalis.utils.yaml_utils import load_eu5_yaml, write_eu5_localization_yaml

if __name__ == "__main__":
    tr_root_dirs = os.listdir(translation_dir)
    moved_file_count = 0
    for tr_dir in tr_root_dirs:
        source_dir_path = Path(os.path.join(str(translation_dir), tr_dir)).resolve()
        machine_translations = list_localization_files("russian_uk_ua_machine_translation", source_dir=source_dir_path)
        post_edited_translations = list_localization_files("russian_uk_ua_post_edited", source_dir=source_dir_path)
        for mt_file in post_edited_translations + machine_translations:
            # post_edited_file = mt_file.replace("_uk_ua_machine_translation", "ukrainian")
            moved_file = mt_file
            # if os.path.exists(post_edited_file):
            #     moved_file = post_edited_file

            relative_path = os.path.relpath(mt_file, source_dir_path)
            output_path = os.path.join(mod_dir, relative_path)
            output_dir, output_fname = os.path.split(output_path)
            # output_dir = os.path.join(output_dir, "eukrainersalis").replace("ukrainian", "english")
            output_dir = output_dir.replace("/russian", "/english/replace")
            output_dir = output_dir.replace("/game/", "/")
            output_fname = output_fname.replace("_uk_ua_machine_translation", "")
            output_fname = output_fname.replace("_l_russian", "_l_english")
            output_path = os.path.join(output_dir, output_fname)
            os.makedirs(output_dir, exist_ok=True)

            content = load_eu5_yaml(moved_file)
            content["l_english"] = content.pop("l_russian")
            write_eu5_localization_yaml(content, output_path)
            moved_file_count += 1
            print(f"Moved {mt_file}\n   -> {output_path}")

    for root, dirs, files in os.walk(project_mod_dir):
        for file in files:
            from_file = os.path.join(root, file)
            rel_path = os.path.relpath(root, project_mod_dir)
            to_dir = os.path.join(mod_dir, rel_path)
            os.makedirs(to_dir, exist_ok=True)
            to_file = os.path.join(to_dir, file)
            shutil.copy(from_file, to_file)
            moved_file_count += 1
            print(f"Moved {from_file}\n   -> {to_file}")

    # mod_custom_localization_dir_path = Path(mod_dir).joinpath(custom_localization_dir_path.relative_to(translation_dir / "game"))
    # os.makedirs(mod_custom_localization_dir_path, exist_ok=True)
    # for root, dirs, files in os.walk(custom_localization_dir_path):
    #     for file in files:
    #         from_file = os.path.join(root, file)
    #         to_file = os.path.join(mod_custom_localization_dir_path, file)
    #         if file.startswith("ua_"):
    #             shutil.copy(os.path.join(root, file), os.path.join(mod_custom_localization_dir_path, file))
    #             print(f"Moved {from_file}\n   -> {to_file}")
    #             moved_file_count += 1
    #             continue
    #         if "_overwrite" in file:
    #             to_file = to_file.replace("_overwrite", "")
    #             shutil.copy(os.path.join(root, file), to_file)
    #             print(f"Moved {from_file}\n   -> {to_file}")
    #             moved_file_count += 1
    #             continue

    print(f"Moved {moved_file_count} files")
