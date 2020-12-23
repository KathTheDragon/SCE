import pytest

from SCE.src import words

def test_word_iter_returns_phones():
    phones = ['a', 'b', 'c', 'd', 'e']
    assert list(Word(phones) == phones

def test_word_parse_adds_surrounding_hashes():
    assert Word.parse('abc').phones == ['#', 'a', 'b', 'c', '#']

def test_word_unparse_strips_surrounding_spaces():
    assert Word(['#', 'a', 'b', 'c', '#']).unparse() == 'abc'
