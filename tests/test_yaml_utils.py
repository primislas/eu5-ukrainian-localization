import os

from eukrainersalis.utils.yaml_utils import fix_concept_declarations, load_eu5_yaml, write_eu5_localization_yaml


def test_yaml_bool_keys_preservation():
    test_file = "test_bool_keys_preservation.yml"
    # Content with keys that PyYAML normally treats as booleans
    raw_content = "l_english:\n  YES: \"Yes\"\n  No: \"No\"\n  ON: \"On\"\n  OFF: \"Off\"\n  True: \"True\"\n  False: \"False\"\n"
    
    try:
        with open(test_file, "w", encoding="utf-8") as f:
            f.write(raw_content)
            
        # 1. Test Loading
        content = load_eu5_yaml(test_file)
        localization = content.get("l_english", {})
        
        expected_keys = ["YES", "No", "ON", "OFF", "True", "False"]
        for key in expected_keys:
            assert key in localization, f"Key '{key}' should be present"
            assert isinstance(key, str), f"Key '{key}' should be a string"
            
        # 2. Test Writing and Reloading
        write_eu5_localization_yaml(content, test_file)
        reloaded_content = load_eu5_yaml(test_file)
        reloaded_localization = reloaded_content.get("l_english", {})
        
        for key in expected_keys:
            assert key in reloaded_localization, f"Key '{key}' should be present after write-back"
            assert isinstance(key, str), f"Key '{key}' should be a string after write-back"
            
        # 3. Test for NO quotes in written-back file
        with open(test_file, "r", encoding="utf-8") as f:
            raw_output = f.read()
            # We check if YES and No are followed by colon and NOT enclosed in quotes
            # Note: the file might start with a BOM if it was written with utf-8-sig
            assert "  YES: \"Yes\"" in raw_output, f"Key 'YES' should be unquoted in output: {raw_output}"
            assert "  No: \"No\"" in raw_output, f"Key 'No' should be unquoted in output: {raw_output}"
            assert "  'YES'" not in raw_output, f"Key 'YES' should NOT be quoted in output: {raw_output}"
            assert "  'No'" not in raw_output, f"Key 'No' should NOT be quoted in output: {raw_output}"
            
    finally:
        if os.path.exists(test_file):
            os.remove(test_file)

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
