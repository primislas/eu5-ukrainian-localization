import json
import os
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path

from eukrainersalis.utils.log_utils import logger
from eukrainersalis.utils.yaml_utils import write_eu5_localization_yaml_async, load_eu5_yaml_async, load_eu5_yaml


class Language(StrEnum):
    ENGLISH = "english"
    UKRAINIAN = "ukrainian"
    RUSSIAN = "russian"
    POLISH = "polish"
    UK_UA_MACHINE_TRANSLATION = "russian_uk_ua_machine_translation"

    def __new__(cls, value):
        member = str.__new__(cls, value)
        member._value_ = value
        member.localization_key = f"l_{value}"
        return member


class SystemInstruction(StrEnum):
    EN_UA = "en_ua"
    RU_UA = "ru_ua"


@dataclass
class LocFile:
    """Encompasses a file path and keys that need to be processed."""
    file_path: str
    selected_keys: list[str] = field(default_factory=list)
    content: dict[str, dict[str, str]] = field(default_factory=dict)
    localization_key: str = Language.RUSSIAN.localization_key
    processed_keys: list[str] = field(default_factory=list)

    def contains(self, key: str) -> bool:
        return key in self.selected_keys

    def select_values(self) -> dict[str, str]:
        localization = self.get_localization()
        return {key: localization.get(key, "") for key in self.selected_keys}

    def get_localization(self) -> dict[str, str]:
        return self.content.get(self.localization_key, {})

    def set_localization(self, localization: dict[str, str]):
        self.content[self.localization_key] = localization

    def set_localization_value(self, loc_key: str, loc_value: str):
        localization = self.get_localization()
        localization[loc_key] = loc_value
        self.set_localization(localization)
        if loc_key not in self.processed_keys:
            self.processed_keys.append(loc_key)

    def __hash__(self) -> int:
        return hash(self.file_path)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, LocFile):
            return NotImplemented
        return self.file_path == other.file_path


@dataclass
class TranslationResult:
    total_records: int = 0
    total_submitted_records: int = 0
    translated_records: int = 0
    submitted_records: list[tuple[str, str]] = field(default_factory=list)
    translated_localizations: dict[str, str] = field(default_factory=dict)
    errors: list[Exception] = field(default_factory=list)
    file_path: Path | str | None = None

    def is_success(self) -> bool:
        return self.translated_records == self.total_submitted_records and not self.errors

    @property
    def untranslated_records(self) -> int:
        return self.total_submitted_records - self.translated_records

    def add_error(self, error: Exception) -> "TranslationResult":
        self.errors.append(error)
        return self

    def add(self, another: "TranslationResult") -> "TranslationResult":
        self.total_records += another.total_records
        self.total_submitted_records += another.total_submitted_records
        self.translated_records += another.translated_records
        self.errors.extend(another.errors)
        return self

    def get_submitted_loc_keys(self) -> list[str]:
        return [t[0] for t in self.submitted_records]

    def get_translated_loc_keys(self) -> list[str]:
        return list(self.translated_localizations.keys())


@dataclass
class TranslationLocKeyFileManager:
    def __init__(self, loc_files: list[LocFile]):
        self._file_by_loc_key: dict[str, LocFile] = {}
        self._file_by_file_path: dict[str, LocFile] = {}
        for loc_file in loc_files:
            self._file_by_file_path[loc_file.file_path] = loc_file
            for loc_key in loc_file.selected_keys:
                self._file_by_loc_key[loc_key] = loc_file

        self._translated_keys = {}

    def add_translated_keys(self, translated_keys: dict[str, str]) -> list[LocFile]:
        loc_files = set()
        for loc_key, loc_value in translated_keys.items():
            loc_key_file = self._file_by_loc_key.get(loc_key)
            if not loc_key_file:
                logger.warning(f"Loc key {loc_key} not found in any loc file")
                continue
            else:
                loc_key_file.set_localization_value(loc_key, loc_value)
                loc_files.add(loc_key_file)
            translated_file_keys = self._translated_keys.get(loc_key_file.file_path, set())
            translated_file_keys.add(loc_key)
            self._translated_keys[loc_key_file.file_path] = translated_file_keys
        return list(loc_files)

    async def write_translated_keys(self, translated_keys: dict[str, str]) -> list[LocFile]:
        loc_files = self.add_translated_keys(translated_keys)
        for loc_file in loc_files:
            file_name = os.path.basename(loc_file.file_path)
            logger.info(f"Translated {len(loc_file.processed_keys)}/{len(loc_file.selected_keys)} keys in {file_name}")
            await write_eu5_localization_yaml_async(loc_file.content, loc_file.file_path)
        return loc_files

    def is_file_translated(self, loc_file: LocFile) -> bool:
        total_file_loc_keys = len(loc_file.selected_keys)
        total_translated_loc_keys = len(self._translated_keys.get(loc_file.file_path, set()))
        return total_translated_loc_keys == total_file_loc_keys

    def get_localization_files(self, loc_keys: list[str]) -> list[LocFile]:
        return list({self._file_by_loc_key[loc_key] for loc_key in loc_keys})

    def get_translated_files(self, loc_keys: list[str]) -> list[LocFile]:
        return [f for f in self.get_localization_files(loc_keys) if self.is_file_translated(f)]


PENDING_TRANSLATION = "PENDING_TRANSLATION"
POSTEDIT_TRANSLATION_FAILURE = "POSTEDIT_TRANSLATION_FAILURE"
POSTEDIT_EMPTY_TRANSLATION = "POSTEDIT_EMPTY_TRANSLATION"
POSTEDIT_MINOR_CHANGE = "POSTEDIT_MINOR_CHANGE"
MIN_LEVENSHTEIN_MIGRATION_DISTANCE = 5

_UNTRUNSLATED_VALUES = [PENDING_TRANSLATION, POSTEDIT_TRANSLATION_FAILURE, POSTEDIT_EMPTY_TRANSLATION]


def split_into_batches(items: list, batch_size: int, min_last_batch_size: int = 10) -> list[list]:
    """Split items into batches. Merges the last batch into the previous one if it's too small."""
    batches = [items[i:i + batch_size] for i in range(0, len(items), batch_size)]
    if len(batches) > 1 and len(batches[-1]) < min_last_batch_size:
        last_batch = batches.pop()
        batches[-1].extend(last_batch)
    return batches


def text_is_not_translated(text: str) -> bool:
    return any([text == k for k in _UNTRUNSLATED_VALUES])


def text_is_translated(text: str) -> bool:
    return not text_is_not_translated(text)


def translation_not_required(text: str) -> bool:
    return text.isascii() or len(text) == 0


def translation_is_required(text: str) -> bool:
    return not translation_not_required(text)


def is_valid_json_object(value: str) -> bool:
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return False

    return isinstance(parsed, dict)


def file_is_untranslated(input_file_path, output_file_path, language: Language | str | None = None, language_key: str | None = None) -> bool:
    """
    Check if a localization file contains untranslated keys.
    """
    localization_key = language_key or Language(language or Language.ENGLISH).localization_key
    input_content = load_eu5_yaml(input_file_path)
    input_localization: dict[str, str] = input_content.get(localization_key, {})
    output_content = load_eu5_yaml(output_file_path)
    output_localization: dict[str, str] = output_content.get(localization_key, {})

    # Key mismatch - re-translation is required
    if input_localization.keys() != output_localization.keys():
        return True

    for k, v in output_localization.items():
        if text_is_not_translated(v):
            return True
    return False


def file_is_translated(input_file_path, output_file_path, language: Language | str | None = None, language_key: str | None = None) -> bool:
    return not file_is_untranslated(input_file_path, output_file_path, language, language_key)


async def get_untranslated_keys(file_path, language: Language | str | None = None, language_key: str | None = None) -> dict[str, str]:
    """
    Check if a localization file contains untranslated keys.
    """
    localization_key = language_key or Language(language or Language.ENGLISH).localization_key
    content = await load_eu5_yaml_async(file_path)
    localization: dict[str, str] = content.get(localization_key, {})
    return {k: v for k, v in localization.items() if text_is_not_translated(v)}


def validate_localization_file(file_path: str, language: Language | str = Language.ENGLISH) -> bool:
    """Validate a YAML localization file by parsing it and checking for errors."""
    try:
        content = load_eu5_yaml(file_path)
        content_key = Language(language).localization_key
        has_english_content = content_key in content and bool(content.get(content_key))
        if not has_english_content:
            logger.debug(f"{file_path} has no {language} localization")
        return has_english_content
    except Exception:
        logger.exception(f"Error parsing {file_path}")
        return False
