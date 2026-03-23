from eukrainersalis.run_machine_translation import expand_concepts, expand_adjectives, translation_postprocessing

def test_expand_concepts_single():
    assert expand_concepts("[locations|e]") == "[Concept('locations', 'CONCEPT_PLACEHOLDER')|e]"

def test_expand_concepts_uppercase():
    assert expand_concepts("[locations|E]") == "[Concept('locations', 'CONCEPT_PLACEHOLDER')|e]"

def test_expand_concepts_mixed_case():
    input_text = "See [locations|E] and [peace|e] for more info."
    expected = "See [Concept('locations', 'CONCEPT_PLACEHOLDER')|e] and [Concept('peace', 'CONCEPT_PLACEHOLDER')|e] for more info."
    assert expand_concepts(input_text) == expected

def test_expand_concepts_with_other_variables():
    input_text = "Дипломатичний статус [COUNTRY.GetName] НЕ дозволяє створення [alliance|e] з [TARGET_COUNTRY.GetName]."
    expected = "Дипломатичний статус [COUNTRY.GetName] НЕ дозволяє створення [Concept('alliance', 'CONCEPT_PLACEHOLDER')|e] з [TARGET_COUNTRY.GetName]."
    assert expand_concepts(input_text) == expected

def test_expand_concepts_multiple():
    input_text = "See [locations|e] and [peace|e] for more info."
    expected = "See [Concept('locations', 'CONCEPT_PLACEHOLDER')|e] and [Concept('peace', 'CONCEPT_PLACEHOLDER')|e] for more info."
    assert expand_concepts(input_text) == expected

def test_expand_concepts_already_expanded():
    text = "[Concept('locations', 'CONCEPT_PLACEHOLDER')|e]"
    assert expand_concepts(text) == text

def test_expand_concepts_no_match():
    text = "Just some plain text."
    assert expand_concepts(text) == text

def test_expand_adjectives_get_adjective():
    # Not in exclusions, so it SHOULD be wrapped.
    assert expand_adjectives("[OTHER.GetAdjective|l]") == "#L [OTHER.GetAdjective|l]#!"

def test_expand_adjectives_adjective_func():
    assert expand_adjectives("[Adjective('friendly')|l]") == "#L [Adjective('friendly')|l]#!"

def test_expand_adjectives_multiple():
    # "COUNTRY.GetAdjective" is excluded, so it is NOT wrapped.
    # "Adjective('hostile')" is NOT excluded, so it IS wrapped.
    input_text = "The [COUNTRY.GetAdjective|l] army and [Adjective('hostile')|l] forces."
    expected = "The [COUNTRY.GetAdjective|l] army and #L [Adjective('hostile')|l]#! forces."
    assert expand_adjectives(input_text) == expected

def test_expand_adjectives_exclusions():
    # Excluded: "AdjectiveWithNoTooltip", ":actor.GetReligion.GetGroup.GetAdjective", "COUNTRY.GetAdjective", "TARGET_COUNTRY.GetAdjective"
    # Wait, the prompt says "the match (including square brackets) should be replaced with #L <matched_value_with_square_brackets>#!"
    # BUT "COUNTRY.GetAdjective" IS in the exclusion list in the code.
    # Let's re-read the code.
    
    # from ukrainersalis_utils/run_machine_translation.py:
    # exclusions = [
    #     "AdjectiveWithNoTooltip",
    #     ":actor.GetReligion.GetGroup.GetAdjective",
    #     "COUNTRY.GetAdjective",
    #     "TARGET_COUNTRY.GetAdjective"
    # ]
    # for exclusion in exclusions:
    #     if exclusion in matched_value:
    #         return matched_value
    
    # So [COUNTRY.GetAdjective|l] should NOT be wrapped.
    assert expand_adjectives("[COUNTRY.GetAdjective|l]") == "[COUNTRY.GetAdjective|l]"
    assert expand_adjectives("[AdjectiveWithNoTooltip|l]") == "[AdjectiveWithNoTooltip|l]"

def test_expand_adjectives_mixed():
    input_text = "[COUNTRY.GetAdjective|l] and [OTHER.GetAdjective|l]"
    # "COUNTRY.GetAdjective" is excluded. "OTHER.GetAdjective" is NOT.
    expected = "[COUNTRY.GetAdjective|l] and #L [OTHER.GetAdjective|l]#!"
    assert expand_adjectives(input_text) == expected

def test_translation_postprocessing():
    input_text = "In [locations|e], the [OTHER.GetAdjective|l] leader sought [peace|e]."
    expected = "In [Concept('locations', 'CONCEPT_PLACEHOLDER')|e], the #L [OTHER.GetAdjective|l]#! leader sought [Concept('peace', 'CONCEPT_PLACEHOLDER')|e]."
    assert translation_postprocessing(input_text) == expected

def test_expand_concepts_multiple_with_other_content():
    input_text = "Before [first|e] middle [second|e] after."
    expected = "Before [Concept('first', 'CONCEPT_PLACEHOLDER')|e] middle [Concept('second', 'CONCEPT_PLACEHOLDER')|e] after."
    assert expand_concepts(input_text) == expected

def test_translation_postprocessing_multiple_matches():
    input_text = "See [locations|e] and [peace|e] for the [OTHER.GetAdjective|l] [Adjective('hostile')|l] forces."
    expected = (
        "See [Concept('locations', 'CONCEPT_PLACEHOLDER')|e] and [Concept('peace', 'CONCEPT_PLACEHOLDER')|e] "
        "for the #L [OTHER.GetAdjective|l]#! #L [Adjective('hostile')|l]#! forces."
    )
    assert translation_postprocessing(input_text) == expected
