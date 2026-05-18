import json
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path


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
class TranslationResult:
    total_records: int = 0
    submitted_records: int = 0
    translated_records: int = 0
    errors: list[Exception] = field(default_factory=list)
    file_path: Path | str | None = None

    def is_success(self) -> bool:
        return self.translated_records == self.submitted_records and not self.errors

    @property
    def untranslated_records(self) -> int:
        return self.submitted_records - self.translated_records

    def add_error(self, error: Exception) -> "TranslationResult":
        self.errors.append(error)
        return self

    def add(self, another: "TranslationResult") -> "TranslationResult":
        self.total_records += another.total_records
        self.submitted_records += another.submitted_records
        self.translated_records += another.translated_records
        self.errors.extend(another.errors)
        return self


PENDING_TRANSLATION = "PENDING_TRANSLATION"
POSTEDIT_TRANSLATION_FAILURE = "POSTEDIT_TRANSLATION_FAILURE"
POSTEDIT_EMPTY_TRANSLATION = "POSTEDIT_EMPTY_TRANSLATION"
POSTEDIT_MINOR_CHANGE = "POSTEDIT_MINOR_CHANGE"
MIN_LEVENSHTEIN_MIGRATION_DISTANCE = 5

_UNTRUNSLATED_VALUES = [PENDING_TRANSLATION, POSTEDIT_TRANSLATION_FAILURE, POSTEDIT_EMPTY_TRANSLATION]


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
