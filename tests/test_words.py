import pytest

from SCE.src import words

def test_word_iter_returns_phones():
    phones = ['a', 'b', 'c', 'd', 'e']
    assert list(words.Word(phones) == phones

def test_word_parse_adds_surrounding_hashes():
    assert words.Word.parse('abc').phones == ['#', 'a', 'b', 'c', '#']

def test_word_unparse_strips_surrounding_spaces():
    assert words.Word(['#', 'a', 'b', 'c', '#']).unparse() == 'abc'

def test_parse_rejects_characters_not_in_graphemes():
    with pytest.raises(InvalidCharacter,
    match=r"^Encountered character 'a' not in graphemes \[b c d\]$"):
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
