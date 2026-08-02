import os
import shutil
from pathlib import Path

from eukrainersalis.run_machine_translation import key_preprocessing, migrated_text_preprocessing
from eukrainersalis.utils.file_utils import game_dir, translation_dir, list_localization_files, \
    custom_localization_game_dir_path, custom_localization_translation_dir_path, list_gui_files
from eukrainersalis.utils.log_utils import logger
from eukrainersalis.utils.migration_utils import normalize_double_quotes
from eukrainersalis.utils.translation_utils import Language
from eukrainersalis.utils.yaml_utils import load_eu5_yaml, write_eu5_localization_yaml


_KEEP_AS_IS_FILES: set[str] = {
    "cw_localize_l_russian.yml",
    "localization_commands_l_russian.yml",
}


def copy_custom_loc():
    for root, dirs, files in os.walk(custom_localization_game_dir_path):
        for file in files:
            source_file = os.path.join(root, file)
            target_file = custom_localization_translation_dir_path / file
            os.makedirs(os.path.dirname(target_file), exist_ok=True)
            shutil.copy(source_file, target_file)
            logger.info(f"Copied custom loc {file} to {target_file}")

    for root, dirs, files in os.walk(custom_localization_translation_dir_path):
        for file in files:
            source_file = os.path.join(root, file)
            target_file = custom_localization_game_dir_path / file
            if not os.path.exists(target_file):
                os.remove(source_file)
                logger.info(f"Deleted custom loc {file} from {source_file}")


def copy_localizations(source_dir: Path, target_dir: Path, languages: list[str]) -> list[str]:
    localization_files = list_localization_files(languages, source_dir)
    print(f"Identified {len(localization_files)} localization files")
    localization_files.sort()
    copied_files = []
    for file in localization_files:
        rel = Path(file).relative_to(source_dir)
        target_file = target_dir / rel
        print(f"Copying {os.path.basename(file)} to {target_file}")
        os.makedirs(os.path.dirname(target_file), exist_ok=True)
        shutil.copy(file, target_file)
        copied_files.append(target_file)
    copied_files.sort()
    return copied_files


def remove_deleted_localizations(source_dir: Path, target_dir: Path, languages: list[str]):
    localization_files = list_localization_files(languages, target_dir)
    print(f"Identified {len(localization_files)} localization files")
    localization_files.sort()
    for file in localization_files:
        rel = Path(file).relative_to(target_dir)
        source_file = source_dir / rel
        if "machine_translation" in file:
            if "_ua_end_" in file:
                # Keeping ending files close to source because it's just more convenient to manage
                continue
            mtr_source_file = str(source_file).replace("_l_russian_uk_ua_machine_translation", "_l_russian")
            if not os.path.exists(mtr_source_file):
                print(f"Deleting {rel}")
                os.remove(file)
        elif not os.path.exists(source_file):
            print(f"Deleting {rel}")
            os.remove(file)


def copy_gui_files(source_dir: Path, target_dir: Path) -> list[str]:
    gui_files = list_gui_files(source_dir)
    print(f"Identified {len(gui_files)} GUI files")
    gui_files.sort()
    copied_files = []
    for file in gui_files:
        rel = Path(file).relative_to(source_dir)
        target_file = target_dir / rel
        print(f"Copying {os.path.basename(file)} to {target_file}")
        os.makedirs(os.path.dirname(target_file), exist_ok=True)
        shutil.copy(file, target_file)
        copied_files.append(target_file)
    copied_files.sort()
    return copied_files


def remove_deleted_gui_files(source_dir: Path, target_dir: Path):
    gui_files = list_gui_files(target_dir)
    print(f"Identified {len(gui_files)} GUI files")
    gui_files.sort()
    for file in gui_files:
        rel = Path(file).relative_to(target_dir)
        source_file = source_dir / rel
        if not os.path.exists(source_file):
            print(f"Deleting removed source file: {rel}")
            os.remove(file)


def validate_and_fix_localization_file(file_path: Path, fix_double_quotes: bool = False):
    in_declaration = False
    indent = -1
    is_patched = False
    validated_lines = []
    line_no = 0
    removed_versioning = 0
    removed_tab_symbols = 0
    adjusted_indent = 0
    escaped_double_quotes = 0
    for line in file_path.read_text(encoding="utf-8-sig").splitlines():
        line_no += 1

        # YAML reader doesn't allow tab symbols
        orig_len = len(line)
        line = line.replace(":\t\"", ": \"")
        line = line.replace("\t", "")
        if len(line) != orig_len:
            removed_tab_symbols += 1

        # We don't support YAML versioning, but there are a few loc files with versioning
        orig_len = len(line)
        line = line.replace(":0 \"", ": \"")
        if len(line) != orig_len:
            removed_versioning += 1

        lstrip = line.lstrip()
        line_indent = len(line) - len(lstrip)

        if not lstrip:
            # Empty line, skipping
            validated_lines.append(line)
            continue

        # 1.2.2 bug
        if lstrip.startswith("0: "):
            lstrip = lstrip[2:].lstrip()
            is_patched = True

        if not lstrip.startswith("#"):
            if fix_double_quotes:
                orig_len = len(lstrip)
                lstrip = normalize_double_quotes(lstrip)
                if len(lstrip) != orig_len:
                    escaped_double_quotes += 1

            if not in_declaration:
                in_declaration = True
                validated_lines.append(lstrip)
                continue

            # detecting first encountered indentation as file level indentation
            if indent <= 0:
                if line_indent > 0:
                    indent = line_indent
                else:
                    indent = 1
            validated_lines.append(" " * indent + lstrip)
            if line_indent != indent:
                adjusted_indent += 1
        else:
            validated_lines.append(line)

    if removed_tab_symbols > 0:
        logger.debug(f"Removed tab symbols from {removed_tab_symbols} lines at {file_path}")
    if removed_versioning > 0:
        logger.debug(f"Removed versioning from {removed_versioning} lines at {file_path}")
    if adjusted_indent > 0:
        logger.debug(f"Fixed invalid indentation in {file_path}")
    if escaped_double_quotes > 0:
        logger.debug(f"Escaped double quotes in {escaped_double_quotes} lines at {file_path}")
    is_patched = is_patched or adjusted_indent > 0 or removed_tab_symbols > 0 or removed_versioning > 0 or escaped_double_quotes > 0

    if is_patched and validated_lines:
        with open(file_path, "w", encoding="utf-8-sig") as f:
            f.write(validated_lines[0])
            for line in validated_lines[1:]:
                f.write("\n")
                f.write(line)
        logger.info(f"Fixed yaml issues with {file_path}")


def normalize_localization_files(source_dir: Path):
    for file in list_localization_files([Language.ENGLISH], source_dir):
        if os.path.basename(file) in _KEEP_AS_IS_FILES:
            continue
        try:
            # Only making them parsearble, no other preprocessing
            validate_and_fix_localization_file(Path(file), fix_double_quotes=True)
        except Exception as e:
            print(f"Error processing {file}: {e}")

    for file in list_localization_files([Language.RUSSIAN], source_dir):
        if os.path.basename(file) in _KEEP_AS_IS_FILES:
            continue
        try:
            validate_and_fix_localization_file(Path(file))
            content = load_eu5_yaml(file)
            localization = content.get(Language.RUSSIAN.localization_key, {}) or {}
            migrated_localization = {key_preprocessing(k): migrated_text_preprocessing(v) for k, v in localization.items()}
            content[Language.RUSSIAN.localization_key] = migrated_localization
            write_eu5_localization_yaml(content, file, indent=1)
        except Exception as e:
            print(f"Error processing {file}: {e}")


if __name__ == "__main__":
    _languages = [Language.ENGLISH, Language.RUSSIAN]
    copy_localizations(game_dir, translation_dir, _languages)
    remove_deleted_localizations(game_dir, translation_dir, _languages + [Language.UK_UA_MACHINE_TRANSLATION])
    normalize_localization_files(translation_dir)
    copy_custom_loc()
    copy_gui_files(game_dir, translation_dir)
    remove_deleted_gui_files(game_dir, translation_dir)
