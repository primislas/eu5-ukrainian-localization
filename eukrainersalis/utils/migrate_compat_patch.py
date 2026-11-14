import json
import os
import shutil
from dataclasses import dataclass
from pathlib import Path

from eukrainersalis.utils.file_utils import remove_and_recreate_dir, list_localization_files, rasf_workshop_dir, \
    rasf_project_dir, rasf_steam_mod_id
from eukrainersalis.utils.log_utils import logger
from eukrainersalis.utils.translation_utils import Language, LocFile


@dataclass
class ModManager:
    project_dir: Path
    steam_dir: Path
    steam_id: str
    archive_dir: Path
    mod_tag: str
    _mod_metadata: dict | None = None


    def _get_mod_metadata(self) -> dict:
        if self._mod_metadata is None:
            metadata_file_path = self.project_dir / ".metadata" / "metadata.json"
            self._mod_metadata = json.loads(Path(metadata_file_path).read_text(encoding="utf-8-sig"))
        return self._mod_metadata

    def is_ignored_file(self, file_name: str) -> bool:
        # A simplified hardcode for now, not overengineering, YAGNI
        file_name_without_ext = os.path.splitext(file_name)[0]
        return file_name_without_ext.endswith(self.mod_tag)

    def get_mod_version(self):
        return self._get_mod_metadata()["version"]

    def get_archive_dir(self):
        mod_version = self.get_mod_version()
        return self.archive_dir / f"rasf-{mod_version}"

    def select_project_mod_files(self) -> list[str]:
        selected_files = []
        for root, dirs, files in os.walk(self.project_dir):
            for file in files:
                if not self.is_ignored_file(file):
                    selected_files.append(os.path.join(root, file))
        return selected_files

    def archive_mod(self):
        """Completely removes archive directory and then moves project files into it"""

        logger.info(f"Archiving mod {self._get_mod_metadata()['name']}-{self._get_mod_metadata()['version']}...")

        archive_dir = self.get_archive_dir()
        remove_and_recreate_dir(archive_dir)
        logger.info(f"Archive dir '{archive_dir.name}' cleaned up and ready")

        mod_files = self.select_project_mod_files()
        logger.info(f"Identified {len(mod_files)} files for archiving")
        for file in mod_files:
            rel_path = os.path.relpath(file, self.project_dir)
            target_path = self.archive_dir / rel_path
            target_dir = target_path.parent
            if not target_dir.exists():
                target_dir.mkdir(parents=True)
            shutil.copy(file, target_path)
            logger.info(f"Archived {os.path.basename(file)}")

        logger.info(f"Mod archiving complete: {len(mod_files)} archived to '{archive_dir.name}'")

    def import_mod(self):
        """Copies all localization files from steam_dir to project_dir"""

        localization_files = list_localization_files(Language.ENGLISH, self.steam_dir)
        logger.info(f"Identified {len(localization_files)} localization files")
        localization_files.sort()
        copied_files = []
        for file in localization_files:
            rel = Path(file).relative_to(self.steam_dir)
            target_file = self.project_dir / rel
            logger.info(f"Copying {os.path.basename(file)} to {target_file}")
            os.makedirs(os.path.dirname(target_file), exist_ok=True)
            shutil.copy(file, target_file)
            copied_files.append(target_file)

        metadata_dir = self.steam_dir / ".metadata"
        for root, dirs, files in os.walk(metadata_dir):
            for file in files:
                file_path = os.path.join(root, file)
                rel = Path(file_path).relative_to(self.steam_dir)
                target_file = self.project_dir / rel
                shutil.copy(file_path, target_file)
                copied_files.append(target_file)

        copied_files.sort()
        logger.info(f"Mod import complete: {len(copied_files)} files copied")
        return copied_files

    def prune_deleted_mod_files(self):
        mod_files = list_localization_files(Language.ENGLISH, self.project_dir)
        removed_files = []
        for file in mod_files:
            rel = Path(file).relative_to(self.project_dir)
            target_file = self.steam_dir / rel
            if not target_file.exists():
                os.remove(file)
                translated_file = file.replace(Language.ENGLISH.file_suffix, Language.UK_UA_MACHINE_TRANSLATION.file_suffix)
                removed_files.append(translated_file)
                if os.path.exists(translated_file):
                    os.remove(translated_file)
                    removed_files.append(translated_file)
        logger.info(f"Mod import pruning complete: {len(removed_files)} files removed")

    def get_archive_file_path(self, project_file_path: str | Path) -> Path:
        rel_path = Path(project_file_path).relative_to(self.project_dir)
        return self.archive_dir / rel_path

    def sync_yaml_files_with_english_source(self):
        en_files = list_localization_files(Language.ENGLISH, self.project_dir)
        total_updated_files = 0
        total_updated_keys = 0
        for en_file in en_files:
            en_file_name = os.path.basename(en_file)
            ua_file = Path(en_file.replace(Language.ENGLISH.file_suffix, Language.UK_UA_MACHINE_TRANSLATION.file_suffix))
            if not ua_file.exists():
                shutil.copy(en_file, ua_file)
                continue

            archive_file_path = self.get_archive_file_path(en_file)
            if not archive_file_path.exists():
                logger.info(f"Archive file not found for {os.path.basename(en_file)}, removing corresponding project files")
                # os.remove(en_file)
                # os.remove(ua_file)
                continue

            archive_en_loc_file = LocFile(archive_file_path).load()
            en_loc_file = LocFile(en_file).load()
            ua_loc_file = LocFile(ua_file).load()

            synced_localization = {}
            archive_en_loc = archive_en_loc_file.get_localization()
            ua_loc = ua_loc_file.get_localization()
            updated_keys = []
            for en_key,en_val in en_loc_file.get_localization().items():
                ua_key = en_key
                if not en_key in ua_loc:
                    updated_keys.append(en_key)
                    if en_key.endswith("ukrainian_dialect"):
                        ua_key = en_key.replace("ukrainian_dialect", "ruthenian_language")
                    elif en_key.endswith("ruthenian_language"):
                        ua_key = en_key.replace("ruthenian_language", "ukrainian_dialect")
                if archive_en_loc.get(en_key) != en_val:
                    updated_keys.append(en_key)
                    synced_localization[en_key] = en_val
                else:
                    synced_localization[en_key] = ua_loc.get(ua_key, en_val)
            deleted_ua_keys = ua_loc.keys() - synced_localization.keys()
            updated_keys.extend(deleted_ua_keys)

            if not len(updated_keys):
                logger.debug("No changes detected in %s", en_file_name)
                continue

            ua_loc_file.set_localization(synced_localization)
            ua_loc_file.save()
            total_updated_files += 1
            total_updated_keys += len(updated_keys)
            logger.info("Updated %s keys in %s", len(updated_keys), en_file_name)

        logger.info("Synced translation with source: updated %s keys in %s files", total_updated_keys, total_updated_files)


def migrate_ruthenia_and_steppe_fix():
    archive_dir = Path(os.environ["ARCHIVE_DIR"])
    mod_tag = os.environ["RASF_MOD_TAG"]

    mod_manager = ModManager(
        project_dir=rasf_project_dir,
        steam_dir=rasf_workshop_dir,
        steam_id=rasf_steam_mod_id,
        archive_dir=archive_dir,
        mod_tag=mod_tag,
    )

    # TODO: test if current version equals archived version?
    mod_manager.archive_mod()
    mod_manager.import_mod()
    mod_manager.prune_deleted_mod_files()
    mod_manager.sync_yaml_files_with_english_source()

    # TODO: automatically translate English

    pass


if __name__ == "__main__":
    migrate_ruthenia_and_steppe_fix()
