import pytest

from SCE.src import words

## Word ##

def test_Word_iter_returns_phones():
    phones = ['a', 'b', 'c', 'd', 'e']
    assert list(words.Word(phones) == phones

def test_Word_parse_adds_surrounding_hashes():
    assert words.Word.parse('abc').phones == ['#', 'a', 'b', 'c', '#']

def test_Word_unparse_strips_surrounding_spaces():
    assert words.Word(['#', 'a', 'b', 'c', '#']).unparse() == 'abc'

## parse ##

def test_parse_rejects_characters_not_in_graphemes():
    with pytest.raises(InvalidCharacter,
    match=r"^Encountered character 'a' not in graphemes \[b c d\] while parsing string 'a'$"):
        words.parse('a', ('b', 'c', 'd'))

def test_parse_prefers_longest_grapheme():
    assert words.parse('abc', ('a', 'b', 'c', 'ab', 'bc', 'abc')) == ['abc']

def test_parse_override_with_separator():
    assert words.parse('abc', ('a', 'b', 'c', 'ab', 'bc', 'abc'), '.') == ['abc']
    assert words.parse('a.bc', ('a', 'b', 'c', 'ab', 'bc', 'abc'), '.') == ['a', 'bc']
    assert words.parse('ab.c', ('a', 'b', 'c', 'ab', 'bc', 'abc'), '.') == ['ab', 'c']
    assert words.parse('a.b.c', ('a', 'b', 'c', 'ab', 'bc', 'abc'), '.') == ['a', 'b', 'c']

def test_parse_wildcard_graphemes_match_anything():
    assert words.parse('abc', ('*',)) == ['a', 'b', 'c']
    assert words.parse('abbbcb', ('*b',)) == ['ab', 'bb', 'cb']

## unparse ##

## startswith ##

def test_startswith_returns_false_when_prefix_longer_than_string():
    assert not words.startswith('ab', 'abc')
    assert not words.startswith('ab', 'abc', strict=True)

def test_startswith_returns_false_when_prefix_equals_string_and_strict_is_true():
    assert not words.startswith('ab', 'ab', strict=True)

def test_startswith_returns_false_when_prefix_is_not_a_prefix_of_string():
    assert not words.startswith('ab', 'b')
    assert not words.startswith('ab', 'b', strict=True)

def test_startswith_returns_true_when_prefix_is_a_prefix_of_string():
    assert words.startswith('ab', 'a')
    assert words.startswith('ab', 'ab')
    assert words.startswith('ab', 'a', strict=True)

def test_startswith_allows_star_to_match_any_character():
    assert words.startswith('ab', '*')
    assert words.startswith('ab', 'a*')
    assert words.startswith('ab', '*b')
    assert words.startswith('ab', '**')
    assert not words.startswith('ab', '**', strict=True)
    #
    assert words.startswith('*b', 'a')
    assert words.startswith('*b', 'a*')
    assert words.startswith('*b', 'ab')
    assert not words.startswith('*b', 'ab', strict=True)

## parseWords ##
