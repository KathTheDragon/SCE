import pytest

from SCE.src.words import *

## Word ##

def test_Word_iter_returns_phones():
    phones = ['a', 'b', 'c', 'd', 'e']
    assert list(Word(phones)) == phones

def test_Word_parse_adds_surrounding_hashes():
    assert Word.parse('abc').phones == ['#', 'a', 'b', 'c', '#']

def test_Word_str_strips_surrounding_spaces():
    assert str(Word(['#', 'a', 'b', 'c', '#'])) == 'abc'

def test_Word_replace_returns_new_word_with_match_replaced():
    word = Word(['#', 'a', 'b', 'c', '#'])
    assert word.replace(slice(1, 3), ['1', '2', '3']) == Word(['#', '1', '2', '3', 'c', '#'])
    assert word == Word(['#', 'a', 'b', 'c', '#'])

def test_Word_replace_adds_new_graphemes_to_new_word():
    word = Word(['#', 'a', 'b', 'c', '#'])
    new_word = word.replace(slice(1, 3), ['aa', 'bb'])
    assert new_word.graphemes == ('*', 'aa', 'bb')

## parse ##

def test_parse_rejects_characters_not_in_graphemes():
    with pytest.raises(InvalidCharacter,
    match=r"^Encountered character 'a' not in graphemes \['b', 'c', 'd'\] while parsing string 'a'$"):
        parse('a', ('b', 'c', 'd'))

def test_parse_prefers_longest_grapheme():
    assert parse('abc', ('a', 'b', 'c', 'ab', 'bc', 'abc')) == ['abc']

def test_parse_override_with_separator():
    assert parse('abc', ('a', 'b', 'c', 'ab', 'bc', 'abc'), '.') == ['abc']
    assert parse('a.bc', ('a', 'b', 'c', 'ab', 'bc', 'abc'), '.') == ['a', 'bc']
    assert parse('ab.c', ('a', 'b', 'c', 'ab', 'bc', 'abc'), '.') == ['ab', 'c']
    assert parse('a.b.c', ('a', 'b', 'c', 'ab', 'bc', 'abc'), '.') == ['a', 'b', 'c']

def test_parse_wildcard_graphemes_match_anything():
    assert parse('abc', ('*',)) == ['a', 'b', 'c']
    assert parse('abbbcb', ('*b',)) == ['ab', 'bb', 'cb']

## unparse ##

def test_unparse_joins_word_when_only_monographs():
    assert unparse(('a', 'b', 'c'), ('a', 'b', 'c')) == 'abc'

# Should probably change
def test_unparse_allows_characters_not_in_graphemes():
    assert unparse(('a', 'b', 'c'), ('ph', 'th', 'kh')) == 'abc'

def test_unparse_inserts_separator_in_sequences_matching_multiple_graphemes():
    assert unparse(('a', 'b', 'c'), ('a', 'b', 'c', 'ab', 'bc', 'abc'), '.') == 'a.b.c'
    assert unparse(('ab', 'c'), ('a', 'b', 'c', 'ab', 'bc', 'abc'), '.') == 'ab.c'
    assert unparse(('a', 'bc'), ('a', 'b', 'c', 'ab', 'bc', 'abc'), '.') == 'a.bc'
    assert unparse(('abc',), ('a', 'b', 'c', 'ab', 'bc', 'abc'), '.') == 'abc'

## startswith ##

def test_startswith_returns_false_when_prefix_longer_than_string():
    assert not startswith('ab', 'abc')
    assert not startswith('ab', 'abc', strict=True)

def test_startswith_returns_false_when_prefix_equals_string_and_strict_is_true():
    assert not startswith('ab', 'ab', strict=True)

def test_startswith_returns_false_when_prefix_is_not_a_prefix_of_string():
    assert not startswith('ab', 'b')
    assert not startswith('ab', 'b', strict=True)

def test_startswith_returns_true_when_prefix_is_a_prefix_of_string():
    assert startswith('ab', 'a')
    assert startswith('ab', 'ab')
    assert startswith('ab', 'a', strict=True)

def test_startswith_allows_star_to_match_any_character():
    assert startswith('ab', '*')
    assert startswith('ab', 'a*')
    assert startswith('ab', '*b')
    assert startswith('ab', '**')
    assert not startswith('ab', '**', strict=True)
    #
    assert startswith('*b', 'a')
    assert startswith('*b', 'a*')
    assert startswith('*b', 'ab')
    assert not startswith('*b', 'ab', strict=True)

## matches ##

def test_matches_returns_false_when_strings_are_unequal_lengths():
    assert not matches('abc', 'abcd')
    assert not matches('abc', 'ab')

def test_matches_returns_true_when_strings_are_identical():
    assert matches('abc', 'abc')

def test_matches_allows_star_to_match_any_character():
    assert matches('ab', '**')
    assert matches('ab', 'a*')
    assert matches('ab', '*b')
    assert matches('a*', '**')
    assert matches('a*', '*b')
    assert matches('a*', 'ab')
    assert matches('*b', '**')
    assert matches('*b', 'a*')
    assert matches('*b', 'ab')

## parseWords ##

## combine_graphemes ##

def test_combine_graphemes_concatenates_and_deduplicates_arguments():
    assert combine_graphemes(
        ('a', 'b', 'c', 'd'),
        ['a', 'e', 'f', 'b'],
    ) == ('a', 'b', 'c', 'd', 'e', 'f')
