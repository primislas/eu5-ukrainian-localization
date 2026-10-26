import os
import re
from pathlib import Path

from eukrainersalis.utils.file_utils import translation_dir


def regenerate_gui_file_endings():
    # Walking depth-first
    files_to_remove = []
    for root, dirs, files in os.walk(translation_dir):
        for file in files:
            if file.endswith("_uk_ua.gui"):
                files_to_remove.append(os.path.join(root, file))
    for file in files_to_remove:
        os.remove(file)
        print(f"Removed {file}")

    replacement_regex = r"(Religion\.GetAdjective|(Language(Family)?|Dialect|Culture(Group)?|PopCultureItem)\.GetName)(WithNoTooltip)?(\|[lL])?\]"
    def replace_match(match: re.Match) -> str:
        matched_text = match.group(0)
        replacement = matched_text + "а" if "Dialect" not in matched_text else matched_text + "ий"
        return replacement

    modifications = 0
    modified_files = 0
    for root, dirs, files in os.walk(translation_dir):
        for file in files:
            if file.endswith(".gui"):
                file_modified = False
                path = os.path.join(root, file)
                content = Path(path).read_text(encoding="utf-8")

                # Проголосити державу Німеччина, а не Проголосити Німеччина
                modified_content = content.replace("[Localize('FORM')] [NewCountryCandidate", "[Localize('FORM')] державу [NewCountryCandidate")
                if modified_content != content:
                    modifications += 1
                    file_modified = True
                    print(f"Modified country formation declaration in {file}")

                if "culture_lateral_view.gui" in file:
                    modified_content = modified_content.replace('text = "game_concept_work_of_art"', 'text = "game_concept_works_of_art"')
                    modifications += 1
                    file_modified = True
                    print(f"Modified culture lateral view in {file}")

                modified_content, replaced_count = re.subn(replacement_regex, replace_match, modified_content)
                if replaced_count > 0:
                    modifications += replaced_count
                    file_modified = True
                    print(f"Modified {replaced_count} declarations in {file}")

                if file_modified:
                    out_path = os.path.join(root, file.replace(".gui", "_uk_ua.gui"))
                    Path(out_path).write_text(modified_content, encoding="utf-8")
                    modified_files += 1

    print(f"Modified {modifications} declarations in {modified_files} files")


if __name__ == "__main__":
    regenerate_gui_file_endings()