import os.path
import re
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


def normalize_double_quotes(line: str) -> str:
    """Escape unescaped double quotes inside a YAML localization value, and add a closing quote if absent.

    For example:
      ` some_yaml_key: "lorem "impsum" lorem" ipsum" # ignore quotes " in comments`
    becomes:
      ` some_yaml_key: "lorem \"impsum\" lorem\" ipsum" # ignore quotes " in comments`

    Comment detection (by `#`) has priority over closing-quote detection.  The
    algorithm scans `#` positions from right to left and takes the rightmost one
    where the text before it ends with an unescaped `"` optionally followed by
    whitespace — that `"` is treated as the closing quote and everything from it
    to end-of-line becomes the comment part.  This ensures that `"` characters
    inside a comment are never mistaken for the closing quote of the value.

    If no `#` yields a valid split, the closing quote is the rightmost unescaped
    `"` followed only by optional whitespace (no comment present).

    If no closing quote is found at all, one is appended.
    """
    match = re.match(r'^(\s*\S+:\s*)"(.*)', line)
    if not match:
        return line

    prefix = match.group(1)
    rest = match.group(2)

    # Step 1: find comment boundary via rightmost '#', scanning right-to-left.
    # Accept the first '#' (rightmost) where the text before it contains a valid
    # closing '"': an unescaped '"' followed only by optional whitespace.
    closing_pos = None
    comment_part = ""
    for hash_pos in (i for i in range(len(rest) - 1, -1, -1) if rest[i] == '#'):
        before_hash = rest[:hash_pos]
        for i in range(len(before_hash) - 1, -1, -1):
            if before_hash[i] == '"' and (i == 0 or before_hash[i - 1] != '\\'):
                if re.match(r'^\s*$', before_hash[i + 1:]):
                    closing_pos = i
                    comment_part = rest[i + 1:]
                    break
        if closing_pos is not None:
            break

    # Step 2: if no '#'-anchored comment found, look for a bare closing '"'
    # (rightmost unescaped '"' followed only by optional whitespace).
    if closing_pos is None:
        for i in range(len(rest) - 1, -1, -1):
            if rest[i] == '"' and (i == 0 or rest[i - 1] != '\\'):
                if re.match(r'^\s*$', rest[i + 1:]):
                    closing_pos = i
                    comment_part = rest[i + 1:]
                    break

    if closing_pos is not None:
        value_content = rest[:closing_pos]
    else:
        value_content = rest
        comment_part = ""

    escaped_content = re.sub(r'(?<!\\)"', '\\"', value_content)

    return f'{prefix}"{escaped_content}"{comment_part}'
