import os.path
from dataclasses import dataclass, field
from pathlib import Path

from eukrainersalis.utils.file_utils import project_dir

_DEFAULT_MIGRATION_DATA_DIR = project_dir / "migrations"


@dataclass
class MigrationManager:
    """Keeps track of which updated files (files changed after a EU5 patch)
    have been migrated - differences synced and auto-translated.
    Migrated files are stored in a text file.
    """


    source_version: str
    data_dir: str = _DEFAULT_MIGRATION_DATA_DIR
    
    _migrations_loaded: bool = False
    _migrated_files: set[str] = field(default_factory=set)

    def __post_init__(self):
        pass

    def _get_migration_file_path(self) -> Path:
        return Path(f"{self.data_dir}/migrating-from-{self.source_version}.txt")

    def _ensure_migration_file_exists(self):
        file_path = self._get_migration_file_path()
        if not file_path.exists():
            if not os.path.exists(self.data_dir):
                os.makedirs(self.data_dir)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write("")

    def _load_migrations(self) -> set[str]:
        if self._migrations_loaded:
            return self._migrated_files

        file_path = self._get_migration_file_path()
        if not file_path.exists():
            self._ensure_migration_file_exists()
        else:
            with open(file_path, "r", encoding="utf-8") as f:
                self._migrations_loaded = True
                fs = [l.strip() for l in f.read().splitlines()]
                fs = [f for f in fs if f]
                self._migrated_files = set(fs)

        return self._migrated_files

    def _write_migrations(self):
        file_path = self._get_migration_file_path()
        with open(file_path, "w", encoding="utf-8") as f:
            f.write("\n".join(self._migrated_files))
        self._migrations_loaded = True

    def is_migrated(self, file_path: str) -> bool:
        return file_path in self._load_migrations()

    def mark_migrated(self, file_path: str):
        if file_path not in self._migrated_files:
            self._migrated_files.add(file_path)
            self._write_migrations()

    def clear_migrations(self):
        self._migrated_files.clear()
        self._write_migrations()
