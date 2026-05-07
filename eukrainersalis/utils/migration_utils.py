import os.path
import threading
from dataclasses import dataclass, field
from pathlib import Path

from eukrainersalis.utils.file_utils import project_dir

_DEFAULT_MIGRATION_DATA_DIR = project_dir / "migrations"


@dataclass
class MigrationManager:
    """Keeps track of which updated files (files changed after a EU5 patch)
    have been processed - and as such can be omitted from subsequent runs.
    """

    file_set_id: str
    data_dir: str = _DEFAULT_MIGRATION_DATA_DIR
    
    _processed_files_loaded: bool = False
    _processed_files: set[str] = field(default_factory=set)
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def __post_init__(self):
        pass

    def _get_tracker_file_path(self) -> Path:
        return Path(f"{self.data_dir}/migration-{self.file_set_id}.txt")

    def _ensure_tracker_file_exists(self):
        file_path = self._get_tracker_file_path()
        if not file_path.exists():
            if not os.path.exists(self.data_dir):
                os.makedirs(self.data_dir)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write("")

    def _load_processed_files(self) -> set[str]:
        if self._processed_files_loaded:
            return self._processed_files

        file_path = self._get_tracker_file_path()
        if not file_path.exists():
            self._ensure_tracker_file_exists()
        else:
            with open(file_path, "r", encoding="utf-8") as f:
                self._processed_files_loaded = True
                fs = [l.strip() for l in f.read().splitlines()]
                fs = [f for f in fs if f]
                self._processed_files = set(fs)

        return self._processed_files

    def _store_processed_files(self):
        file_path = self._get_tracker_file_path()
        with open(file_path, "w", encoding="utf-8") as f:
            sorted_files = sorted(self._processed_files)
            f.write("\n".join(sorted_files))
        self._processed_files_loaded = True

    def is_processed(self, file_path: str) -> bool:
        return file_path in self._load_processed_files()

    def mark_processed(self, file_path: str):
        with self._lock:
            if file_path not in self._processed_files:
                self._processed_files.add(file_path)
                self._store_processed_files()

    def clear_processed_files(self):
        with self._lock:
            self._processed_files.clear()
            self._store_processed_files()
