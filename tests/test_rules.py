import pytest
from pytest import fixture, raises

skip = pytest.mark.skip
xfail = pytest.mark.xfail

import random
from dataclasses import dataclass, field, InitVar
from SCE.src import cats, patterns, words
from SCE.src.rules import *

# Mocks
@dataclass
class MockPattern(Pattern):
    elements: list = field(init=False, default_factory=list)
    matches: list[slice]

    def __bool__(self):
        return True

    def resolve(self, target=None):
        return self

    def match(self, word, start=None, stop=None, catixes={}):
        if (start is None) == (stop is None):
            raise TypeError('exactly one of start and stop must be given.')
        elif start is not None:
            for match in self.matches:
                if match.stop > len(word):
                    break
                elif match.start == start:
                    return match, {}
            return None, {}
        else:
            for match in self.matches:
                if match.stop > len(word):
                    break
                elif match.stop == stop:
                    return match, {}
            return None, {}

@dataclass
class MockTarget(Target):
    pattern: Pattern = field(init=False, default=Pattern([]))
    indices: list[int] = field(init=False, default_factory=list)
    matches: list[slice]

    def match(self, word: Word) -> list[tuple[slice, dict[int, int]]]:
        return [(match, {}) for match in self.matches if match.stop <= len(word)]


@dataclass
class MockEnvironment(LocalEnvironment):
    left: Pattern = field(init=False)
    right: Pattern = field(init=False)
    matches: InitVar[list[slice]]

    def __post_init__(self, matches):
        left = []
        right = []
        for match in matches:
            left.append(slice(match.start, match.start))
            right.append(slice(match.stop, match.stop))
        self.left = MockPattern(left)
        self.right = MockPattern(right)

@dataclass
class MockBaseRule(BaseRule):
    flags: Flags

    def _apply(self, word):
        return Word([*word.phones, 'a'])

# Fixtures
@fixture
def word():
    yield Word(['a']*10)

@fixture
def set_random():
    state = random.getstate()
    random.seed(0)
    yield
    random.setstate(state)

## Functions ##

# match_environments
def test_match_environments_returns_true_if_any_environment_group_matches(word):
    env1 = MockEnvironment([slice(3, 5)])
    env2 = MockEnvironment([slice(3, 6)])
    assert match_environments([[env1]], word, slice(3, 5), {})
    assert not match_environments([[env2]], word, slice(3, 5), {})
    assert match_environments([[env1], [env2]], word, slice(3, 5), {})

def test_match_environments_returns_true_if_all_environments_in_a_group_match(word):
    env1 = MockEnvironment([slice(3, 5)])
    env2 = MockEnvironment([slice(3, 6)])
    assert match_environments([[env1]], word, slice(3, 5), {})
    assert not match_environments([[env1, env2]], word, slice(3, 5), {})
    assert match_environments([[env1, env1]], word, slice(3, 5), {})

# overlaps
def test_two_empty_slices_overlap_when_identical():
    assert overlaps(slice(1, 1), slice(1, 1))
    assert not overlaps(slice(1, 1), slice(2, 2))

def test_empty_slice_overlaps_non_empty_slice_when_fully_contained():
    assert overlaps(slice(1, 1), slice(0, 2))
    assert not overlaps(slice(1, 1), slice(1, 2))
    assert not overlaps(slice(1, 1), slice(0, 1))
    assert not overlaps(slice(1, 1), slice(2, 3))

def test_non_empty_slices_overlap_when_ranges_intersect():
    assert overlaps(slice(1, 3), slice(2, 4))
    assert overlaps(slice(1, 4), slice(2, 3))
    assert overlaps(slice(1, 3), slice(1, 2))
    assert overlaps(slice(1, 3), slice(2, 3))
    assert not overlaps(slice(1, 3), slice(3, 4))
    assert not overlaps(slice(1, 2), slice(3, 4))

## Target ##
def test_Target_with_no_indices_returns_all_matches(word):
    pattern = MockPattern([slice(1, 3), slice(2, 7), slice(5, 5), slice(6, 8)])
    assert Target(pattern, []).match(word) == [
        (slice(1, 3), {}),
        (slice(2, 7), {}),
        (slice(5, 5), {}),
        (slice(6, 8), {})
    ]

def test_Target_with_indices_returns_only_indexed_matches(word):
    pattern = MockPattern([slice(1, 3), slice(2, 7), slice(5, 5), slice(6, 8)])
    assert Target(pattern, [1, -1, 2]).match(word) == [
        (slice(2, 7), {}),
        (slice(6, 8), {}),
        (slice(5, 5), {}),
    ]

def test_Target_doesnt_use_out_of_bounds_indices(word):
    pattern = MockPattern([slice(1, 3), slice(2, 7), slice(5, 5), slice(6, 8)])
    assert Target(pattern, [6, -5]).match(word) == []

def test_Target_doesnt_consider_empty_match_at_0(word):
    pattern = MockPattern([slice(0, 0), slice(1, 2), slice(2, 3)])
    assert Target(pattern, []).match(word) == [
        (slice(1, 2), {}),
        (slice(2, 3), {}),
    ]
    assert Target(pattern, [0]).match(word) == [(slice(1, 2), {})]

## LocalEnvironment ##
def test_LocalEnvironment_matches_iff_left_and_right_match(word):
    lenv = LocalEnvironment(
        left=MockPattern([slice(1, 3)]),
        right=MockPattern([slice(5, 6)])
    )
    assert lenv.match(word, slice(3, 5), {})
    assert not lenv.match(word, slice(2, 5), {})
    assert not lenv.match(word, slice(3, 6), {})

def test_LocalEnvironment_passes_catixes_from_left_into_right(word):
    lenv = LocalEnvironment(
        left=patterns.Pattern([patterns.Category(cats.Category(['a', 'b']), 1)]),
        right=patterns.Pattern([patterns.Category(cats.Category(['a', 'c']), 1)])
    )
    assert lenv.match(word, slice(1, 2), {})

    lenv = LocalEnvironment(
        left=patterns.Pattern([patterns.Category(cats.Category(['a', 'b']), 1)]),
        right=patterns.Pattern([patterns.Category(cats.Category(['c', 'a']), 1)])
    )
    assert not lenv.match(word, slice(1, 2), {})

# match_all
def test_LocalEnvironment_match_all_returns_all_indices_where_left_and_right_match(word):
    lenv = LocalEnvironment(
        left=MockPattern([slice(1, 3), slice(2, 8), slice(3, 4), slice(6, 9)]),
        right=MockPattern([slice(2, 6), slice(3, 9), slice(4, 8)])
    )
    assert lenv.match_all(word, slice(1, 2), {}) == [3, 4]

## GlobalEnvironment ##
def test_GlobalEnvironment_with_no_indices_matches_anywhere_in_word(word):
    assert GlobalEnvironment(MockPattern([slice(0, 1)]), []).match(word, slice(1, 2), {})
    assert GlobalEnvironment(MockPattern([slice(3, 7)]), []).match(word, slice(1, 2), {})
    assert GlobalEnvironment(MockPattern([slice(5, 10)]), []).match(word, slice(1, 2), {})

def test_GlobalEnvironment_with_indices_matches_at_any_index(word):
    assert GlobalEnvironment(MockPattern([slice(0, 1)]), [0]).match(word, slice(1, 2), {})
    assert not GlobalEnvironment(MockPattern([slice(0, 1)]), [1]).match(word, slice(1, 2), {})

# match_all
def test_GlobalEnvironment_match_all_returns_all_indices_where_matching_can_happen(word):
    assert GlobalEnvironment(Pattern([]), []).match_all(word, slice(1, 2), {}) == [
        1, 2, 3, 4, 5, 6, 7, 8, 9
    ]

    indices = [2, 4, 5, 8, 9]
    assert GlobalEnvironment(Pattern([]), indices).match_all(word, slice(1, 2), {}) == indices

## Predicate ##

def test_Predicate_doesnt_match_if_exceptions_match(word):
    env1 = MockEnvironment([slice(1, 2)])
    assert not SubstPredicate([], [], [[env1]]).match(word, slice(1, 2), {})
    assert not SubstPredicate([], [[env1]], [[env1]]).match(word, slice(1, 2), {})

def test_Predicate_matches_if_exceptions_dont_match_and_conditions_do_match(word):
    env1 = MockEnvironment([slice(1, 2)])
    env2 = MockEnvironment([slice(2, 3)])
    assert SubstPredicate([], [[env1]], [[env2]]).match(word, slice(1, 2), {})

def test_Predicate_matches_if_exceptions_dont_match_and_no_conditions(word):
    env2 = MockEnvironment([slice(2, 3)])
    assert SubstPredicate([], [], [[env2]]).match(word, slice(1, 2), {})

def test_Predicate_doesnt_match_if_neither_exceptions_not_conditions_match(word):
    env1 = MockEnvironment([slice(1, 2)])
    env2 = MockEnvironment([slice(2, 3)])
    assert not SubstPredicate([], [[env1]], [[env2]]).match(word, slice(1, 3), {})

## SubstPredicate ##

def test_SubstPredicate_get_replacement_converts_indexed_replacement_to_list_str(word):
    pattern = Pattern([patterns.TargetRef(1), patterns.Category(cats.Category(['b', 'c']), 1)])
    assert SubstPredicate([pattern], [], []).get_replacement(word, slice(1, 2), {1: 1}, 0) == ['a', 'c']

def test_SubstPredicate_get_replacement_mods_index_by_len_replacements(word):
    replacements = [
        Pattern([patterns.Grapheme('a')]),
        Pattern([patterns.Grapheme('b')]),
        Pattern([patterns.Grapheme('c')]),
    ]
    assert SubstPredicate(replacements, [], []).get_replacement(word, slice(1, 2), {}, 5) == ['c']

## InsertPredicate ##

def test_InsertPredicate_get_destinations_returns_intersection_of_matches_from_indexed_environments(
        word):
    environments = [
        GlobalEnvironment(Pattern([]), [1, 3, 5, 7, 9]),
        GlobalEnvironment(Pattern([]), [1, 2, 4, 5, 7, 8]),
    ]
    assert InsertPredicate([environments], [], []).get_destinations(word, slice(1, 2), {}, 0) == [1, 5, 7]

def test_InsertPredicate_get_destinations_mods_index_by_len_destinations(word):
    destinations = [
        [GlobalEnvironment(Pattern([]), [1])],
        [GlobalEnvironment(Pattern([]), [2])],
        [GlobalEnvironment(Pattern([]), [3])],
    ]
    assert InsertPredicate(destinations, [], []).get_destinations(word, slice(1, 2), {}, 5) == [3]

## BaseRule ##
def test_BaseRule_randomly_runs_if_chance_flag_is_set(set_random, word):
    # Sequence of randint calls is 50, 98, 54, 6, ...
    rule = MockBaseRule(Flags(chance=50))
    assert rule(word)
    with raises(RuleRandomlySkipped):
        rule(word)
    with raises(RuleRandomlySkipped):
        rule(word)
    assert rule(word)

def test_BaseRule_repeats_according_to_repeat_flag():
    assert MockBaseRule(Flags(repeat=3))(Word([])) == Word(['a', 'a', 'a'])
    assert MockBaseRule(Flags(repeat=0))(Word([])) == Word([])
    assert MockBaseRule(Flags(repeat=2))(Word([])) == Word(['a', 'a'])
    assert MockBaseRule(Flags())(Word([])) == Word(['a'])

## Rule ##

# _get_matches
def test_Rule__get_matches_returns_all_matches_for_each_target(word):
    rule = Rule(
        rule='test',
        targets=[MockTarget([slice(1, 6), slice(2, 8)]), MockTarget([slice(3, 6), slice(4, 5)])],
        predicates=[],
        flags=Flags()
    )
    assert rule._get_matches(word) == [
        (slice(1, 6), {}, 0),
        (slice(2, 8), {}, 0),
        (slice(3, 6), {}, 1),
        (slice(4, 5), {}, 1),
    ]

def test_Rule__get_matches_sorts_by_match_start_then_target_index_if_ltr(word):
    rule = Rule(
        rule='test',
        targets=[MockTarget([slice(1, 6), slice(4, 8)]), MockTarget([slice(3, 6), slice(4, 5)])],
        predicates=[],
        flags=Flags(rtl=0)
    )
    assert rule._get_matches(word) == [
        (slice(1, 6), {}, 0),
        (slice(3, 6), {}, 1),
        (slice(4, 8), {}, 0),
        (slice(4, 5), {}, 1),
    ]

def test_Rule__get_matches_sorts_by_match_stop_reversed_then_target_index_if_rtl(word):
    rule = Rule(
        rule='test',
        targets=[MockTarget([slice(1, 6), slice(4, 8)]), MockTarget([slice(3, 6), slice(4, 5)])],
        predicates=[],
        flags=Flags(rtl=1)
    )
    assert rule._get_matches(word) == [
        (slice(4, 8), {}, 0),
        (slice(1, 6), {}, 0),
        (slice(3, 6), {}, 1),
        (slice(4, 5), {}, 1),
    ]

def test_Rule__get_matches_raises_NoMatchesFound_if_no_matches_are_found(word):
    rule = Rule(rule='test', targets=[], predicates=[])
    with raises(NoMatchesFound):
        rule._get_matches(word)

# _validate_matches

# _apply_changes
def test_Rule__apply_changes_makes_all_replacements(word):
    assert Rule('', [], [])._apply_changes(word, [
        (slice(1, 2), ['b']),
        (slice(3, 4), ['c']),
        (slice(5, 6), ['d']),
    ]) == Word(['a', 'b', 'a', 'c', 'a', 'd', 'a', 'a', 'a', 'a'])

# _apply

## RuleBlock ##

# _apply
