from eukrainersalis.utils.yaml_utils import fix_concept_declarations

def test_fix_concept_declarations_example():
    input_str = "Дипломатичний статус [Concept('COUNTRY.GetName] НЕ дозволяє створення [alliance', 'CONCEPT_PLACEHOLDER')|e] з [TARGET_COUNTRY.GetName]"
    expected_str = "Дипломатичний статус [COUNTRY.GetName] НЕ дозволяє створення [Concept('alliance', 'CONCEPT_PLACEHOLDER')|e] з [TARGET_COUNTRY.GetName]"
    assert fix_concept_declarations(input_str) == expected_str

def test_fix_concept_declarations_multiple():
    input_str = "[Concept('TEXT1] [word_one', 'CONCEPT_PLACEHOLDER')|e] and [Concept('TEXT2] [word_two', 'CONCEPT_PLACEHOLDER')|e]"
    expected_str = "[TEXT1] [Concept('word_one', 'CONCEPT_PLACEHOLDER')|e] and [TEXT2] [Concept('word_two', 'CONCEPT_PLACEHOLDER')|e]"
    assert fix_concept_declarations(input_str) == expected_str

def test_fix_concept_declarations_no_change():
    input_str = "Correct one [Concept('alliance', 'CONCEPT_PLACEHOLDER')|e] and simple [COUNTRY.GetName]"
    assert fix_concept_declarations(input_str) == input_str
