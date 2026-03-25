from eukrainersalis.utils.translation_utils import Language

def test_language_enum_values():
    assert Language.ENGLISH == "english"
    assert Language.UKRAINIAN == "ukrainian"
    assert Language.RUSSIAN == "russian"

def test_language_localization_key():
    assert Language.ENGLISH.localization_key == "l_english"
    assert Language.UKRAINIAN.localization_key == "l_ukrainian"
    assert Language.RUSSIAN.localization_key == "l_russian"

def test_language_initialization_from_str():
    assert Language("english") == Language.ENGLISH
    assert Language("english").localization_key == "l_english"
    assert Language(Language.UKRAINIAN).localization_key == "l_ukrainian"
