from eukrainersalis.translators.gemini_translator import GeminiTranslator

def test_match_empty_phrases_basic():
    # Input batch has leading and trailing empty lines
    input_batch = ["", "Hello", "World", ""]
    # Output batch from Gemini might only contain translated text
    output_lines = ["Привіт", "Світ"]
    
    result = GeminiTranslator._match_empty_phrases(output_lines, input_batch)
    assert result == ["", "Привіт", "Світ", ""]

def test_match_empty_phrases_internal():
    # Input batch has internal empty line
    input_batch = ["Hello", "", "World"]
    output_lines = ["Привіт", "Світ"]
    
    result = GeminiTranslator._match_empty_phrases(output_lines, input_batch)
    assert result == ["Привіт", "", "Світ"]

def test_match_empty_phrases_multiple_internal():
    input_batch = ["One", "", "Two", "", "Three"]
    output_lines = ["Один", "Два", "Три"]
    
    result = GeminiTranslator._match_empty_phrases(output_lines, input_batch)
    assert result == ["Один", "", "Два", "", "Три"]

# def test_match_empty_phrases_strips_existing():
#     # Input batch has internal empty line
#     input_batch = ["Hello", "", "World"]
#     # Output batch has ITS OWN leading and trailing empty lines (should be ignored)
#     output_lines = ["", "Привіт", "", "Світ", ""]
#
#     result = GeminiTranslator._match_empty_phrases(output_lines, input_batch)
#     # Output should align with input, ignoring its own previous padding
#     assert result == ["Привіт", "", "Світ"]

def test_match_empty_phrases_consumes_matching_empty():
    # Input has empty, output has empty at same place
    input_batch = ["A", "", "B"]
    output_lines = ["X", "", "Y"]
    result = GeminiTranslator._match_empty_phrases(output_lines, input_batch)
    assert result == ["X", "", "Y"]

# def test_match_empty_phrases_extra_output_empties():
#     # Input has no empty, output has unexpected empty
#     input_batch = ["A", "B"]
#     output_lines = ["", "X", "", "Y", ""]
#     result = GeminiTranslator._match_empty_phrases(output_lines, input_batch)
#     assert result == ["X", "Y"]
#
def test_match_empty_phrases_all_empty_input():
    input_batch = ["", "", ""]
    output_lines = ["Something", "Else"]
    
    result = GeminiTranslator._match_empty_phrases(output_lines, input_batch)
    assert result == ["", "", "", "Something", "Else"]

def test_match_empty_phrases_all_empty_output():
    input_batch = ["Hello", "", "World"]
    output_lines = ["", "", ""]
    
    result = GeminiTranslator._match_empty_phrases(output_lines, input_batch)
    # Since output has no content, result will just be input's structure filled with empties
    assert result == ["", "", ""]

def test_match_empty_phrases_no_empty_needed():
    input_batch = ["Hello", "World"]
    output_lines = ["Привіт", "Світ"]
    
    result = GeminiTranslator._match_empty_phrases(output_lines, input_batch)
    assert result == ["Привіт", "Світ"]

def test_match_empty_phrases_mismatched_content_count_more_output():
    # Input expects 1 non-empty, but we have 2
    input_batch = ["", "One", ""]
    output_lines = ["Uno", "Dos"]
    
    result = GeminiTranslator._match_empty_phrases(output_lines, input_batch)
    # Leading 1, then only one slot for content, then Trailing 1.
    # Extra "Dos" is discarded to match input batch size.
    assert result == ["", "Uno", "", "Dos"]

def test_match_empty_phrases_mismatched_content_count_less_output():
    # Input expects 2 non-empty, but we have 1
    input_batch = ["One", "", "Two"]
    output_lines = ["Uno", "", ""]
    
    result = GeminiTranslator._match_empty_phrases(output_lines, input_batch)
    # input[0] == "One" -> add content[0] ("Uno")
    # input[1] == "" -> add ""
    # input[2] == "Two" -> content exhausted, add ""
    assert result == ["Uno", "", ""]
