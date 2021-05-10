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
class MockPatternElement(SubpatternMixin, Element):
    pattern: Pattern = field(init=False)
    length: InitVar[int]

    def __post_init__(self, length):
        self.pattern = MockPattern(length)

@dataclass
class MockPattern(Pattern):
    elements: list[Element] = field(init=False, default_factory=list)
    length: int

    def _match(self, word, start=None, stop=None):
        if (start is None) == (stop is None):
            raise TypeError('exactly one of start and stop must be given.')
        elif start is None:
            if 0 < stop <= len(word):
                return self.length
            else:
                raise MatchFailed()
        else:
            if 0 <= start < len(word):
                return self.length
            else:
                raise MatchFailed()

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

def test_CharacterMixin_match_returns_one_when_does_match():
    assert MockCharacterElement(matches=True).match(['a'], start=0) == 1
    assert MockCharacterElement(matches=True).match(['a'], stop=1) == 1

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

@xfail(reason='module cats is unimplemented')
def test_Category_match():
    word = [...]
    assert cats.Category(...)._match(word, ...)

## Wildcard ##

# Wildcard._match
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

# Wildcard._match_pattern
def test_Wildcard_matches_at_least_one_regardless_of_greedy():
    pattern = MockPattern(length=1)
    word = ['#', '#']
    with raises(MatchFailed):
        Wildcard(greedy=True, extended=False)._match_pattern(pattern, word, start=0)
    with raises(MatchFailed):
        Wildcard(greedy=False, extended=False)._match_pattern(pattern, word, start=0)

    word = ['a']
    with raises(MatchFailed):
        Wildcard(greedy=True, extended=False)._match_pattern(pattern, word, start=0)
    with raises(MatchFailed):
        Wildcard(greedy=False, extended=False)._match_pattern(pattern, word, start=0)

def test_Wildcard_with_greedy_True_matches_longest_run():
    pattern = MockPattern(length=1)
    word = ['a', 'a', 'a', 'a', '#', '#']
    assert Wildcard(greedy=True, extended=False)._match_pattern(pattern, word, start=0) == 5
    assert Wildcard(greedy=True, extended=False)._match_pattern(pattern, word, stop=4) == 4
    assert Wildcard(greedy=True, extended=True)._match_pattern(pattern, word, start=0) == 6
    assert Wildcard(greedy=True, extended=True)._match_pattern(pattern, word, stop=6) == 6

def test_Wildcard_with_greedy_False_matches_shortest_run():
    pattern = MockPattern(length=1)
    word = ['a', 'a', 'a', 'a', '#', '#']
    assert Wildcard(greedy=False, extended=False)._match_pattern(pattern, word, start=0) == 2
    assert Wildcard(greedy=False, extended=False)._match_pattern(pattern, word, stop=4) == 2
    assert Wildcard(greedy=False, extended=True)._match_pattern(pattern, word, start=0) == 2
    assert Wildcard(greedy=False, extended=True)._match_pattern(pattern, word, stop=6) == 2

## SubpatternMixin ##

def test_SubpatternMixin_match_returns_length_of_pattern():
    word = ['a', 'a']
    assert MockPatternElement(length=2).match(word, start=0) == 2
    assert MockPatternElement(length=2).match(word, stop=2) == 2

## Repetition ##

def test_Repetition_matches_pattern_number_times():
    subpattern = MockPattern(length=2)
    element = Repetition(pattern=subpattern, number=2)
    pattern = MockPattern(length=1)
    word = ['a']*5
    assert element._match_pattern(pattern, word, start=0) == 5
    assert element._match_pattern(pattern, word, stop=5) == 5

    word = ['a']*4
    with raises(MatchFailed):
        element._match_pattern(pattern, word, start=0)

## WildcardRepetition ##

def test_WildcardRepetition_matches_at_least_one_regardless_of_greedy():
    subpattern = MockPattern(length=2)
    element_greedy = WildcardRepetition(pattern=subpattern, greedy=True)
    element_nongreedy = WildcardRepetition(pattern=subpattern, greedy=False)
    pattern = MockPattern(length=1)
    word = ['a']
    with raises(MatchFailed):
        element_greedy._match_pattern(pattern, word, start=0)
    with raises(MatchFailed):
        element_nongreedy._match_pattern(pattern, word, start=0)

    word = ['a', 'a']
    with raises(MatchFailed):
        element_greedy._match_pattern(pattern, word, start=0)
    with raises(MatchFailed):
        element_nongreedy._match_pattern(pattern, word, start=0)

def test_WildcardRepetition_with_greedy_True_matches_longest_run():
    subpattern = MockPattern(length=2)
    element = WildcardRepetition(pattern=subpattern, greedy=True)
    pattern = MockPattern(length=1)
    word = ['a']*6
    assert element._match_pattern(pattern, word, start=0) == 5
    assert element._match_pattern(pattern, word, stop=6) == 5

def test_WildcardRepetition_with_greedy_False_matches_shortest_run():
    subpattern = MockPattern(length=2)
    element = WildcardRepetition(pattern=subpattern, greedy=False)
    pattern = MockPattern(length=1)
    word = ['a']*6
    assert element._match_pattern(pattern, word, start=0) == 3
    assert element._match_pattern(pattern, word, stop=6) == 3

## Optional ##

def test_Optional_with_greedy_True_matches_self_if_possible():
    subpattern = MockPattern(length=2)
    element = Optional(pattern=subpattern, greedy=True)
    pattern = MockPattern(length=1)
    word = ['a']
    assert element._match_pattern(pattern, word, start=0) == 1
    assert element._match_pattern(pattern, word, stop=1) == 1

    word = ['a', 'a']
    assert element._match_pattern(pattern, word, start=0) == 1
    assert element._match_pattern(pattern, word, stop=2) == 1

    word = ['a', 'a', 'a']
    assert element._match_pattern(pattern, word, start=0) == 3
    assert element._match_pattern(pattern, word, stop=3) == 3

def test_Optional_with_greedy_False_doesnt_match_self_if_possible():
    subpattern = MockPattern(length=2)
    element = Optional(pattern=subpattern, greedy=False)
    pattern = MockPattern(length=1)
    word = ['a', 'a', 'a']
    assert element._match_pattern(pattern, word, start=0) == 1
    assert element._match_pattern(pattern, word, stop=3) == 1

## Pattern ##
