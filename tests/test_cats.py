import pytest
from pytest import raises

skip = pytest.mark.skip
xfail = pytest.mark.xfail

from dataclasses import dataclass, field, InitVar
from SCE.src import cats

# Category.parse
def test_parse_looks_up_names_in_categories_dict():
    cons = cats.Category(['p', 't', 'k', 's', 'h', 'm', 'n', 'r', 'l'], 'cons')
    vowel = cats.Category(['a', 'e', 'i', 'o', 'u'], 'vowel')
    assert cats.Category.parse('cons', categories={'cons': cons, 'vowel': vowel}) is cons


def test_parse_splits_on_comma():
    assert cats.Category.parse('a,b,c', categories={}).elements == ['a', 'b', 'c']


def test_parse_ignores_empty_elements():
    assert cats.Category.parse(',,,', categories={}).elements == []


def test_parse_takes_elements_only_in_all_categories_separated_by_ampersand():
    assert cats.Category.parse('a,b,c&b,c,d&c,d,e', categories={}).elements == ['c']


def test_parse_takes_elements_from_first_category_not_in_other_categories_separated_by_minus():
    assert cats.Category.parse('a,b,c-b,-c,', categories={}).elements == ['a']


def test_parse_combines_categories_separated_by_pipe_or_plus():
    assert cats.Category.parse('a,|b,+c,', categories={}).elements == ['a', 'b', 'c']
