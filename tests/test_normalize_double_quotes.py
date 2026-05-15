from eukrainersalis.utils.migration_utils import normalize_double_quotes


# --- lines that don't match the YAML key pattern: returned unchanged ---

def test_no_match_plain_text():
    assert normalize_double_quotes("no yaml key here") == "no yaml key here"

def test_no_match_empty_string():
    assert normalize_double_quotes("") == ""

def test_no_match_value_without_opening_quote():
    line = " some_key: value without quotes"
    assert normalize_double_quotes(line) == line


# --- docstring example ---

def test_docstring_example():
    inp = ' some_yaml_key: "lorem "impsum" lorem" ipsum" # ignore quotes " in comments'
    expected = ' some_yaml_key: "lorem \\"impsum\\" lorem\\" ipsum" # ignore quotes " in comments'
    assert normalize_double_quotes(inp) == expected


# --- clean value: no interior quotes, nothing to escape ---

def test_clean_value_no_interior_quotes():
    assert normalize_double_quotes(' key: "hello world"') == ' key: "hello world"'


# --- interior unescaped quotes are escaped ---

def test_single_interior_unescaped_quote():
    assert normalize_double_quotes(' key: "foo "bar" baz"') == ' key: "foo \\"bar\\" baz"'

def test_multiple_interior_unescaped_quotes():
    assert normalize_double_quotes(' key: "a "b" c "d" e"') == ' key: "a \\"b\\" c \\"d\\" e"'


# --- already-escaped quotes are left alone ---

def test_already_escaped_quotes_not_double_escaped():
    assert normalize_double_quotes(r' key: "foo \"bar\" baz"') == r' key: "foo \"bar\" baz"'


# --- closing quote absent: one is added ---

def test_missing_closing_quote():
    assert normalize_double_quotes(' key: "hello world') == ' key: "hello world"'

def test_missing_closing_quote_with_interior_quotes():
    assert normalize_double_quotes(' key: "foo "bar" baz') == ' key: "foo \\"bar\\" baz"'


# --- comment preservation ---

def test_comment_after_closing_quote_preserved():
    line = ' key: "value" # a comment'
    assert normalize_double_quotes(line) == ' key: "value" # a comment'

def test_comment_with_quotes_not_escaped():
    line = ' key: "value" # ignore quotes " in comments'
    assert normalize_double_quotes(line) == ' key: "value" # ignore quotes " in comments'

def test_interior_quotes_escaped_comment_preserved():
    line = ' key: "foo "bar"" # note'
    result = normalize_double_quotes(line)
    assert result.endswith('# note')
    assert '\\"bar\\"' in result


# --- whitespace after closing quote ---

def test_trailing_whitespace_after_closing_quote():
    line = ' key: "value"   '
    result = normalize_double_quotes(line)
    assert result.startswith(' key: "value"')


# --- '#' has priority: quotes inside a comment are never escaped ---

def test_quote_in_comment_not_treated_as_closing_quote():
    # The '"' inside the comment must not be mistaken for the closing quote.
    line = ' key: "value" # comment "with quotes"'
    assert normalize_double_quotes(line) == ' key: "value" # comment "with quotes"'

def test_hash_inside_value_not_treated_as_comment():
    # '#' that is inside the quoted value (no '"' precedes it with only whitespace)
    # must not split off a comment.
    line = ' key: "value #T markup"'
    assert normalize_double_quotes(line) == ' key: "value #T markup"'

def test_multiple_hashes_rightmost_valid_split_wins():
    # Rightmost '#' is inside the comment text; the second '#' is the real comment start.
    line = ' key: "value" # comment with #hash'
    assert normalize_double_quotes(line) == ' key: "value" # comment with #hash'

def test_hash_in_value_and_hash_in_comment():
    # '#' appears both inside the value (#T markup) and as a comment marker.
    line = ' key: "foo #T bar" # actual comment'
    assert normalize_double_quotes(line) == ' key: "foo #T bar" # actual comment'
