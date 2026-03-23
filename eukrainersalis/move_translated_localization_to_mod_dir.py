import os
import shutil
from pathlib import Path

from eukrainersalis.utils.file_utils import list_localization_files, translation_dir, mod_dir

if __name__ == "__main__":
    tr_root_dirs = os.listdir(translation_dir)
    moved_file_count = 0
    for tr_dir in tr_root_dirs:
        source_dir_path = Path(os.path.join(translation_dir, tr_dir)).resolve()
        machine_translations = list_localization_files("russian_uk_ua_machine_translation", source_dir=source_dir_path)
        for mt_file in machine_translations:
            # post_edited_file = mt_file.replace("_uk_ua_machine_translation", "ukrainian")
            moved_file = mt_file
            # if os.path.exists(post_edited_file):
            #     moved_file = post_edited_file

            relative_path = os.path.relpath(mt_file, source_dir_path)
            output_path = os.path.join(mod_dir, relative_path)
            output_dir, output_fname = os.path.split(output_path)
            # output_dir = os.path.join(output_dir, "eukrainersalis").replace("ukrainian", "english")
            output_dir = output_dir.replace("/russian", "/russian/replace")
            output_fname = output_fname.replace("_uk_ua_machine_translation", "")
            output_path = os.path.join(output_dir, output_fname)

            os.makedirs(output_dir, exist_ok=True)
            shutil.copy(moved_file, output_path)
            moved_file_count += 1
            print(f"Moved {mt_file}\n\t-> {output_path}")
    print(f"Moved {moved_file_count} files")
