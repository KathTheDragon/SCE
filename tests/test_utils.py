import pytest
from pytest import raises

skip = pytest.mark.skip
xfail = pytest.mark.xfail

from dataclasses import dataclass, field, InitVar
from SCE.src import utils

# find
def test_find_returns_lowest_index_any_substring_starts_at():
    assert utils.find('abc', 'a', 'b', 'c') == 0
    assert utils.find('abcdefg', 'bc', 'ef') == 1


def test_find_returns_minus_1_if_no_substring_found():
    assert utils.find('abc', 'd', 'e', 'f') == -1


def test_find_ignores_escaped_characters():
    assert utils.find(r'a\bcb', 'b') == 4
    assert utils.find(r'a\bc', 'b') == -1


def test_find_skips_over_matched_brackets():
    assert utils.find('a(b)b', 'b') == 4
    assert utils.find('a[b]b', 'b') == 4
    assert utils.find('a{b}b', 'b') == 4
    assert utils.find('a([({[(b)]})])b', 'b') == 14
    assert utils.find('a(b)') == -1


def test_find_rejects_strings_containing_unmatched_brackets():
    with raises(ValueError):
        utils.find('a(b', 'b')
    with raises(ValueError):
        utils.find('a)b', 'b')


def test_find_is_constrained_to_search_between_start_and_stop():
    assert utils.find('abc', 'b', start=2) == -1
    assert utils.find('abc', 'b', stop=1) == -1


# contains

# match_bracket
def test_match_bracket_returns_index_of_closing_bracket_matching_opening_bracket_at_start():
    assert utils.match_bracket('(abc)', 0) == 4
    assert utils.match_bracket('[abc]', 0) == 4
    assert utils.match_bracket('{abc}', 0) == 4
    assert utils.match_bracket('(a(b(c)))', 0) == 8
    assert utils.match_bracket('(a(b(c)))', 2) == 7
    assert utils.match_bracket('(a(b(c)))', 4) == 6


def test_match_bracket_rejects_index_that_does_not_point_to_a_bracket():
    with raises(ValueError):
        utils.match_bracket('(abc)', 1)


def test_match_bracket_rejects_incorrect_closing_bracket():
    with raises(ValueError):
        utils.match_bracket('(abc]', 0)


def test_match_bracket_rejects_unclosed_bracket():
    with raises(ValueError):
        utils.match_bracket('(abc', 0)


# split
...
