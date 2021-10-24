import pytest
from pytest import raises

skip = pytest.mark.skip
xfail = pytest.mark.xfail

from dataclasses import dataclass, field, InitVar
from SCE.src import cats
from SCE.src.patterns import *

# Mocks
@dataclass(eq=False)
class MockCharacterElement(CharacterMixin, Element):
    matches: bool

    def __str__(self):
        return str(self.matches)

    def _match(self, word, index):
        return self.matches

@dataclass(repr=False, eq=False)
class MockWildcardElement(WildcardMixin, CharacterMixin, Element):
    def _match(self, word, index):
        return word[index] != '#'

@dataclass(repr=False, eq=False)
class MockPatternElement(SubpatternMixin, Element):
    pattern: Pattern = field(init=False)
    length: InitVar[int]

    def __post_init__(self, length):
        self.pattern = MockPattern(length)

@dataclass
class MockPattern(Pattern):
    elements: list[Element] = field(init=False, default_factory=list)
    length: int

    def _match(self, word, start=None, stop=None, catixes={}):
        advance(word, self.length, start, stop)
        return self.length, catixes

## Functions ##

# advance
def test_advance_requires_either_start_or_stop():
    word = ['a']
    with raises(TypeError):
        advance(word, 1)
    with raises(TypeError):
        advance(word, 1, start=0, stop=0)

def test_advance_start_must_be_at_least_zero():
    word = ['a']
    with raises(MatchFailed):
        advance(word, 1, start=-1)

def test_advance_start_must_be_at_most_len_word_minus_length():
    word = ['a']
    with raises(MatchFailed):
        advance(word, 1, start=1)

def test_advance_stop_must_be_at_least_length():
    word = ['a']
    with raises(MatchFailed):
        advance(word, 1, stop=0)

def test_advance_stop_must_be_at_most_len_word():
    word = ['a']
    with raises(MatchFailed):
        advance(word, 1, stop=2)

def test_advance_returns_start_plus_length_None_if_given_start():
    word = ['a']
    assert advance(word, 1, start=0) == (1, None)

def test_advance_returns_None_stop_minus_length_if_given_stop():
    word = ['a']
    assert advance(word, 1, stop=1) == (None, 0)

# get_index
def test_get_index_requires_either_start_or_stop():
    word = ['a']
    with raises(TypeError):
        get_index(word)
    with raises(TypeError):
        get_index(word, start=0, stop=0)

def test_get_index_start_must_be_at_least_zero():
    word = ['a', 'b', 'c']
    assert get_index(word, start=0) == 0
    with raises(MatchFailed):
        get_index(word, start=-1)

def test_get_index_start_must_be_less_than_len_word():
    word = ['a', 'b', 'c']
    assert get_index(word, start=2) == 2
    with raises(MatchFailed):
        get_index(word, start=3)

def test_get_index_stop_must_be_greater_than_zero():
    word = ['a', 'b', 'c']
    assert get_index(word, stop=1) == 0
    with raises(MatchFailed):
        get_index(word, stop=0)

def test_get_index_stop_must_be_at_most_len_word():
    word = ['a', 'b', 'c']
    assert get_index(word, stop=3) == 2
    with raises(MatchFailed):
        get_index(word, stop=4)

def test_get_index_returns_start__or_stop_minus_one():
    word = ['a', 'b', 'c']
    assert get_index(word, start=1) == 1
    assert get_index(word, stop=1) == 0

## CharacterMixin ##

def test_CharacterMixin_match_raises_MatchFailed_when_doesnt_match():
    with raises(MatchFailed):
        MockCharacterElement(matches=False).match(['a'], start=0)

def test_CharacterMixin_match_returns_1_and_catixes_when_does_match():
    assert MockCharacterElement(matches=True).match(['a'], start=0, catixes={1: 2}) == (1, {1: 2})
    assert MockCharacterElement(matches=True).match(['a'], stop=1, catixes={1: 2}) == (1, {1: 2})

## Grapheme ##

def test_Grapheme_matches_same_character():
    word = ['a']
    assert Grapheme(grapheme='a')._match(word, 0)

def test_Grapheme_doesnt_match_different_character():
    word = ['b']
    assert not Grapheme(grapheme='a')._match(word, 0)

## Ditto ##

def test_Ditto_doesnt_match_first_character():
    word = ['a']
    assert not Ditto()._match(word, 0)

def test_Ditto_doesnt_match_unpaired_character():
    word = ['a', 'b']
    assert not Ditto()._match(word, 1)

def test_Ditto_doesnt_match_first_character_of_pair():
    word = ['a', 'b', 'b']
    assert not Ditto()._match(word, 1)

def test_Ditto_does_match_second_character_of_pair():
    word = ['a', 'b', 'b']
    assert Ditto()._match(word, 2)

## Category ##

def test_Category_without_subscript_matches_any_grapheme_it_contains():
    word = ['a', 'b', 'c', 'd']
    category = Category(cats.Category(['a', 'b']), None)
    assert category.match(word, start=0, catixes={1: 2}) == (1, {1: 2})
    assert category.match(word, start=1, catixes={1: 2}) == (1, {1: 2})
    with raises(MatchFailed):
        category.match(word, start=2, catixes={1: 2})
    with raises(MatchFailed):
        category.match(word, start=3, catixes={1: 2})

def test_Category_with_subscript_in_catixes_only_matches_indexed_grapheme():
    word = ['a', 'b', 'c', 'd']
    category = Category(cats.Category(['a', 'b', 'c', 'd']), 1)
    with raises(MatchFailed):
        category.match(word, start=0, catixes={1: 2})
    with raises(MatchFailed):
        category.match(word, start=1, catixes={1: 2})
    assert category.match(word, start=2, catixes={1: 2}) == (1, {1: 2})
    with raises(MatchFailed):
        category.match(word, start=3, catixes={1: 2})

def test_Category_with_subscript_not_in_catixes_matches_any_grapheme_it_contains_and_adds_subscript_to_catixes():
    word = ['a', 'b', 'c', 'd']
    category = Category(cats.Category(['a', 'b']), 0)
    assert category.match(word, start=0, catixes={1: 2}) == (1, {0: 0, 1: 2})
    assert category.match(word, start=1, catixes={1: 2}) == (1, {0: 1, 1: 2})
    with raises(MatchFailed):
        category.match(word, start=2, catixes={1: 2})
    with raises(MatchFailed):
        category.match(word, start=3, catixes={1: 2})

## WildcardMixin

def test_WildcardMixin_matches_at_least_once_regardless_of_greedy():
    pattern = MockPattern(length=1)
    word = ['#', '#']
    with raises(MatchFailed):
        MockWildcardElement(greedy=False).match_pattern(pattern, word, start=0, catixes={1: 2})
    with raises(MatchFailed):
        MockWildcardElement(greedy=True).match_pattern(pattern, word, start=0, catixes={1: 2})

    word = ['a']
    with raises(MatchFailed):
        MockWildcardElement(greedy=False).match_pattern(pattern, word, start=0, catixes={1: 2})
    with raises(MatchFailed):
        MockWildcardElement(greedy=True).match_pattern(pattern, word, start=0, catixes={1: 2})

def test_WildcardMixin_with_greedy_True_matches_longest_run():
    pattern = MockPattern(length=1)
    word = ['a', 'a', 'a', 'a', '#', '#']
    assert MockWildcardElement(greedy=True).match_pattern(pattern, word, start=0, catixes={1: 2}) == (5, {1: 2})
    assert MockWildcardElement(greedy=True).match_pattern(pattern, word, stop=4, catixes={1: 2}) == (4, {1: 2})

def test_WildcardMixin_with_greedy_False_matches_shortest_run():
    pattern = MockPattern(length=1)
    word = ['a', 'a', 'a', 'a', '#', '#']
    assert MockWildcardElement(greedy=False).match_pattern(pattern, word, start=0, catixes={1: 2}) == (2, {1: 2})
    assert MockWildcardElement(greedy=False).match_pattern(pattern, word, stop=4, catixes={1: 2}) == (2, {1: 2})

# Using WildcardRepetition in these because it inherits from SubpatternMixin with no overrides
def test_WildcardMixin_adds_catixes_from_self_match():
    subpattern = Pattern([Category(cats.Category(['a', 'b']), 1)])
    pattern = MockPattern(length=1)
    word = ['a', '#']
    assert WildcardRepetition(subpattern, greedy=True).match_pattern(pattern, word, start=0) == (2, {1: 0})

def test_WildcardMixin_uses_same_catixes_for_multiple_iterations():
    subpattern = Pattern([Category(cats.Category(['a', 'b']), 1)])
    pattern = MockPattern(length=1)
    word = ['a', 'a', '#']
    assert WildcardRepetition(subpattern, greedy=True).match_pattern(pattern, word, start=0) == (3, {1: 0})

    word = ['a', 'b', '#']
    assert WildcardRepetition(subpattern, greedy=True).match_pattern(pattern, word, start=0) == (2, {1: 0})

def test_WildcardMixin_adds_catixes_from_pattern_match():
    subpattern = Pattern([Grapheme('a')])
    pattern = Pattern([Category(cats.Category(['b', 'c']), 1)])
    word = ['a', 'a', 'b']
    assert WildcardRepetition(subpattern, greedy=True).match_pattern(pattern, word, start=0) == (3, {1: 0})

def test_WildcardMixin_uses_catixes_from_self_match_in_pattern_match():
    subpattern = Pattern([Category(cats.Category(['a', 'b']), 1)])
    pattern = Pattern([Category(cats.Category(['b', 'c']), 1)])
    word = ['a', 'a', 'b']
    assert WildcardRepetition(subpattern, greedy=True).match_pattern(pattern, word, start=0) == (3, {1: 0})

    word = ['a', 'a', 'c']
    with raises(MatchFailed):
        WildcardRepetition(subpattern, greedy=True).match_pattern(pattern, word, start=0)

## Wildcard ##

def test_Wildcard_with_extended_False_doesnt_match_hash():
    word = ['#']
    assert not Wildcard(greedy=True, extended=False)._match(word, 0)

def test_Wildcard_with_extended_True_does_match_hash():
    word = ['#']
    assert Wildcard(greedy=True, extended=True)._match(word, 0)

def test_Wildcard_matches_anything_else_regardless_of_extended():
    word = ['a']
    assert Wildcard(greedy=True, extended=False)._match(word, 0)
    assert Wildcard(greedy=True, extended=True)._match(word, 0)

## SubpatternMixin ##

def test_SubpatternMixin_match_returns_length_of_pattern():
    word = ['a', 'a']
    assert MockPatternElement(length=2).match(word, start=0, catixes={1: 2}) == (2, {1: 2})
    assert MockPatternElement(length=2).match(word, stop=2, catixes={1: 2}) == (2, {1: 2})

## Repetition ##

def test_Repetition_matches_pattern_number_times():
    subpattern = MockPattern(length=2)
    element = Repetition(pattern=subpattern, number=2)
    pattern = MockPattern(length=1)
    word = ['a']*5
    assert element.match_pattern(pattern, word, start=0, catixes={1: 2}) == (5, {1: 2})
    assert element.match_pattern(pattern, word, stop=5, catixes={1: 2}) == (5, {1: 2})

    word = ['a']*4
    with raises(MatchFailed):
        element.match_pattern(pattern, word, start=0, catixes={1: 2})

def test_Repetition_adds_catixes_from_self_match():
    subpattern = Pattern([Category(cats.Category(['a', 'b']), 1)])
    pattern = MockPattern(length=1)
    word = ['a', '#']
    assert Repetition(subpattern, number=1).match_pattern(pattern, word, start=0) == (2, {1: 0})

def test_Repetition_uses_same_catixes_for_all_iterations():
    subpattern = Pattern([Category(cats.Category(['a', 'b']), 1)])
    pattern = MockPattern(length=1)
    word = ['a', 'a', '#']
    assert Repetition(subpattern, number=2).match_pattern(pattern, word, start=0) == (3, {1: 0})

    word = ['a', 'b', '#']
    with raises(MatchFailed):
        Repetition(subpattern, number=2).match_pattern(pattern, word, start=0)

def test_Repetition_adds_catixes_from_pattern_match():
    subpattern = Pattern([Grapheme('a')])
    pattern = Pattern([Category(cats.Category(['b', 'c']), 1)])
    word = ['a', 'a', 'b']
    assert Repetition(subpattern, number=2).match_pattern(pattern, word, start=0) == (3, {1: 0})

def test_Repetition_uses_catixes_from_self_match_in_pattern_match():
    subpattern = Pattern([Category(cats.Category(['a', 'b']), 1)])
    pattern = Pattern([Category(cats.Category(['b', 'c']), 1)])
    word = ['a', 'a', 'b']
    assert Repetition(subpattern, number=2).match_pattern(pattern, word, start=0) == (3, {1: 0})

    word = ['a', 'a', 'c']
    with raises(MatchFailed):
        Repetition(subpattern, number=2).match_pattern(pattern, word, start=0)

## WildcardRepetition ##

## Optional ##

def test_Optional_with_greedy_True_matches_self_if_possible():
    subpattern = MockPattern(length=2)
    element = Optional(pattern=subpattern, greedy=True)
    pattern = MockPattern(length=1)
    word = ['a']
    assert element.match_pattern(pattern, word, start=0, catixes={1: 2}) == (1, {1: 2})
    assert element.match_pattern(pattern, word, stop=1, catixes={1: 2}) == (1, {1: 2})

    word = ['a', 'a']
    assert element.match_pattern(pattern, word, start=0, catixes={1: 2}) == (1, {1: 2})
    assert element.match_pattern(pattern, word, stop=2, catixes={1: 2}) == (1, {1: 2})

    word = ['a', 'a', 'a']
    assert element.match_pattern(pattern, word, start=0, catixes={1: 2}) == (3, {1: 2})
    assert element.match_pattern(pattern, word, stop=3, catixes={1: 2}) == (3, {1: 2})

def test_Optional_with_greedy_False_doesnt_match_self_if_possible():
    subpattern = MockPattern(length=2)
    element = Optional(pattern=subpattern, greedy=False)
    pattern = MockPattern(length=1)
    word = ['a', 'a', 'a']
    assert element.match_pattern(pattern, word, start=0, catixes={1: 2}) == (1, {1: 2})
    assert element.match_pattern(pattern, word, stop=3, catixes={1: 2}) == (1, {1: 2})

def test_Optional_adds_catixes_from_self_match_if_self_matches():
    subpattern = Pattern([Category(cats.Category(['a', 'b']), 1)])
    pattern = MockPattern(length=1)
    word = ['a', '#']
    assert Optional(subpattern, greedy=True).match_pattern(pattern, word, start=0) == (2, {1: 0})
    assert Optional(subpattern, greedy=False).match_pattern(pattern, word, start=0) == (1, {})

    pattern = Pattern([Grapheme('#')])
    assert Optional(subpattern, greedy=False).match_pattern(pattern, word, start=0) == (2, {1: 0})

    word = ['#']
    assert Optional(subpattern, greedy=True).match_pattern(pattern, word, start=0) == (1, {})
    assert Optional(subpattern, greedy=False).match_pattern(pattern, word, start=0) == (1, {})

def test_Optional_adds_catixes_from_pattern_match():
    subpattern = Pattern([Grapheme('a')])
    pattern = Pattern([Category(cats.Category(['b', 'c']), 1)])
    word = ['a', 'b']
    assert Optional(subpattern, greedy=True).match_pattern(pattern, word, start=0) == (2, {1: 0})

    word = ['b']
    assert Optional(subpattern, greedy=True).match_pattern(pattern, word, start=0) == (1, {1: 0})

def test_Optional_uses_catixes_from_self_match_in_pattern_match():
    subpattern = Pattern([Category(cats.Category(['a', 'b']), 1)])
    pattern = Pattern([Category(cats.Category(['b', 'c']), 1)])
    word = ['a', 'b']
    assert Optional(subpattern, greedy=True).match_pattern(pattern, word, start=0) == (2, {1: 0})

    word = ['a', 'c']
    with raises(MatchFailed):
        Optional(subpattern, greedy=True).match_pattern(pattern, word, start=0)

## Pattern ##
def test_Pattern_is_truthy_iff_not_empty():
    assert not Pattern([])
    assert Pattern([Grapheme('a')])

# Pattern.resolve
def test_Pattern_resolve_replaces_percent_with_target():
    pattern = Pattern([TargetRef(1)])
    assert pattern.resolve('ab') == Pattern([Grapheme('a'), Grapheme('b')])

def test_Pattern_resolve_replaces_left_arrow_with_reversed_target():
    pattern = Pattern([TargetRef(-1)])
    assert pattern.resolve('ab') == Pattern([Grapheme('b'), Grapheme('a')])

def test_Pattern_resolve_recurses_into_Repetition_WildcardRepetition_Optional():
    pattern = Pattern([
        Repetition(Pattern([TargetRef(1)]), 3),
        WildcardRepetition(Pattern([TargetRef(1)]), True),
        Optional(Pattern([TargetRef(1)]), True),
    ])
    assert pattern.resolve('a') == Pattern([
        Repetition(Pattern([Grapheme('a')]), 3),
        WildcardRepetition(Pattern([Grapheme('a')]), True),
        Optional(Pattern([Grapheme('a')]), True),
    ])

# Pattern.as_phones
def test_Pattern_as_phones_converts_Grapheme_to_string():
    pattern = Pattern([Grapheme('a'), Grapheme('b'), Grapheme('c')])
    assert pattern.as_phones('') == ['a', 'b', 'c']

def test_Pattern_as_phones_Ditto_copies_previous_string():
    pattern = Pattern([Grapheme('a'), Ditto()])
    assert pattern.as_phones('') == ['a', 'a']

    pattern = Pattern([Grapheme('a'), Ditto(), Ditto()])
    assert pattern.as_phones('') == ['a', 'a', 'a']

    pattern = Pattern([Ditto()])
    assert pattern.as_phones('a') == ['a']

def test_Pattern_as_phones_indexes_Category_if_subscript_in_catixes():
    pattern = Pattern([
        Category(cats.Category(['a', 'b', 'c']), 1),
        Category(cats.Category(['d', 'e', 'f']), 2),
        Category(cats.Category(['g', 'h', 'i']), 1),
    ])
    assert pattern.as_phones('', {1: 2, 2: 0}) == ['c', 'd', 'i']

def test_Pattern_as_phones_raises_ValueError_if_Category_subscript_not_in_catixes():
    pattern = Pattern([
        Category(cats.Category(['a', 'b', 'c']), 1),
        Category(cats.Category(['d', 'e', 'f']), 2),
        Category(cats.Category(['g', 'h', 'i']), 1),
    ])
    with raises(ValueError):
        pattern.as_phones('', {1: 2})

def test_Pattern_as_phones_Repetition_repeats_internal_pattern():
    pattern = Pattern([Repetition(Pattern([Grapheme('a')]), 3)])
    assert pattern.as_phones('') == ['a', 'a', 'a']

    pattern = Pattern([Repetition(Pattern([Ditto(), Grapheme('b')]), 2)])
    assert pattern.as_phones('a') == ['a', 'b', 'b', 'b']

    pattern = Pattern([Repetition(Pattern([Category(cats.Category(['a', 'b', 'c']), 1)]), 3)])
    assert pattern.as_phones('', {1: 2}) == ['c', 'c', 'c']

def test_Pattern_as_phones_disallows_other_element_types():
    with raises(TypeError):
        Pattern([Category(None)]).as_phones('')
    with raises(TypeError):
        Pattern([Wildcard(False, False)]).as_phones('')
    with raises(TypeError):
        Pattern([WildcardRepetition(Pattern([]), False)]).as_phones('')
    with raises(TypeError):
        Pattern([Optional(Pattern([]), False)]).as_phones('')

# Pattern._match
def test_Pattern_match_requires_exactly_one_of_start_and_stop():
    with raises(TypeError):
        Pattern([])._match([])
    with raises(TypeError):
        Pattern([])._match([], start=0, stop=0)

def test_Pattern_match_raises_MatchFailed_on_failed_matches():
    with raises(MatchFailed):
        Pattern([Grapheme('a')])._match(['b'], start=0)

def test_Pattern_match_sums_lengths_of_element_matches():
    char_elem = MockCharacterElement(True)
    patt_elem = MockPatternElement(3)
    pattern = Pattern([char_elem, char_elem, patt_elem, char_elem, patt_elem])
    word = ['a']*10
    assert pattern._match(word, start=0, catixes={1: 2}) == (9, {1: 2})
    assert pattern._match(word, stop=10, catixes={1: 2}) == (9, {1: 2})

# Pattern.match
def test_Pattern_match():
    pattern = MockPattern(length=2)
    word = ['a', 'a']
    assert pattern.match(word, start=0, catixes={1: 2}) == (Match(0, 2), {1: 2})
    assert pattern.match(word, stop=2, catixes={1: 2}) == (Match(0, 2), {1: 2})
    assert pattern.match(word, start=1, catixes={1: 2}) == (None, {})
    assert pattern.match(word, stop=1, catixes={1: 2}) == (None, {})
