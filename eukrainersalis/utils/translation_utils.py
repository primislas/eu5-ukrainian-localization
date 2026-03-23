from enum import StrEnum


class Language(StrEnum):
    ENGLISH = "english"
    UKRAINIAN = "ukrainian"
    RUSSIAN = "russian"

    def __new__(cls, value):
        member = str.__new__(cls, value)
        member._value_ = value
        member.localization_key = f"l_{value}"
        return member


class SystemInstruction(StrEnum):
    EN_UA = "en_ua"
    RU_UA = "ru_ua"


PENDING_TRANSLATION = "PENDING_TRANSLATION"
POSTEDIT_TRANSLATION_FAILURE = "POSTEDIT_TRANSLATION_FAILURE"
POSTEDIT_EMPTY_TRANSLATION = "POSTEDIT_EMPTY_TRANSLATION"

_UNTRUNSLATED_VALUES = [PENDING_TRANSLATION, POSTEDIT_TRANSLATION_FAILURE, POSTEDIT_EMPTY_TRANSLATION]


def text_is_not_translated(text: str) -> bool:
    return any([text == k for k in _UNTRUNSLATED_VALUES])


def text_is_translated(text: str) -> bool:
    return not text_is_not_translated(text)


def translation_not_required(text: str) -> bool:
    return text.isascii() or len(text) == 0


def translation_is_required(text: str) -> bool:
    return not translation_not_required(text)
