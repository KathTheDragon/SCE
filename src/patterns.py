import re
from dataclasses import dataclass
from typing import overload
from . import cats, words
from .utils import match_bracket
from .words import Word

ESCAPES = '+-,>/!()[]{}?*"\\$%<'

class MatchFailed(Exception):
    pass

@overload
def advance(word: Word, length: int, start: int, stop: None) -> tuple[int, None]:
    ...
@overload
def advance(word: Word, length: int, start: None, stop: int) -> tuple[None, int]:
    ...
def advance(word, length, start=None, stop=None):
    if (start is None) == (stop is None):
        raise TypeError('exactly one of start and stop must be given.')
    elif start is not None:
        if 0 <= start <= len(word) - length:
            return start + length, None
        else:
            raise MatchFailed()
    else:  # stop is not None
        if length <= stop <= len(word):
            return None, stop - length
        else:
            raise MatchFailed()


def get_index(word: Word, start: int|None=None, stop: int|None=None) -> int:
    if (start is None) == (stop is None):
        raise TypeError('exactly one of start and stop must be given.')
    elif start is not None:
        index = start
    else:  # stop is not None
        index = stop - 1
    if 0 <= index < len(word):
        return index
    else:
        raise MatchFailed()


def Match(start: int, stop: int) -> slice:
    return slice(start, stop)


@dataclass
class Element:
    def __str__(self) -> str:
        return ''

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}({str(self)!r})'

    def match(self, word: Word, start: int|None=None, stop: int|None=None) -> tuple[int, dict[int, int]]:
        if (start is None) == (stop is None):
            raise TypeError('exactly one of start and stop must be given.')
        else:
            raise MatchFailed()

class CharacterMixin:
    def _match(self, word: Word, index: int) -> bool:
        return False

    def match(self, word: Word, start: int|None=None, stop: int|None=None, catixes: dict[int, int]={}) -> tuple[int, dict[int, int]]:
        index = get_index(word, start=start, stop=stop)
        if self._match(word, index):
            return 1, catixes
        else:
            raise MatchFailed()


@dataclass(repr=False)
class Grapheme(CharacterMixin, Element):
    grapheme: str

    def __str__(self) -> str:
        if self.grapheme in ESCAPES:
            return f'\\{self.grapheme}'
        else:
            return self.grapheme

    def _match(self, word: Word, index: int) -> bool:
        return word[index] == self.grapheme


@dataclass(repr=False)
class Ditto(CharacterMixin, Element):
    def __str__(self) -> str:
        return '"'

    def __repr__(self) -> str:
        return 'Ditto()'

    def _match(self, word: Word, index: int) -> bool:
        return index and word[index] == word[index-1]


@dataclass(repr=False)
class Category(Element):
    category: cats.Category
    subscript: int | None

    def __str__(self) -> str:
        string = f'[{self.category}]'
        if self.subscript is not None:
            string += str(self.subscript).translate(str.maketrans('0123456789', '₀₁₂₃₄₅₆₇₈₉'))
        return string

    def match(self, word: Word, start: int|None=None, stop: int|None=None, catixes: dict[int, int]={}) -> tuple[int, dict[int, int]]:
        index = get_index(word, start=start, stop=stop)
        # Note that this will change if sequences become supported in categories
        if self.subscript is None:
            if word[index] in self.category:
                return 1, catixes
        elif self.subscript in catixes:
            if word[index] == self.category[catixes[self.subscript]]:
                return 1, catixes
        else:
            if word[index] in self.category:
                return 1, catixes | {self.subscript: self.category.index(word[index])}

        raise MatchFailed()


@dataclass(repr=False)
class BranchMixin:
    greedy: bool

    def match_pattern(self, pattern: 'Pattern', word: Word, start: int|None=None, stop: int|None=None, catixes: dict[int, int]={}) -> tuple[int, dict[int, int]]:
        if self.greedy:
            try:
                return self._match_branch(pattern, word, start, stop, catixes)
            except MatchFailed:
                return pattern._match(word, start, stop, catixes)
        else:
            try:
                return pattern._match(word, start, stop, catixes)
            except:
                return self._match_branch(pattern, word, start, stop, catixes)


@dataclass(repr=False)
class WildcardMixin(BranchMixin):
    def _match_branch(self, pattern: 'Pattern', word: Word, start:int|None=None, stop: int|None=None, catixes: dict[int, int]={}) -> tuple[int, dict[int, int]]:
        return self.match_pattern(pattern, word, start, stop, catixes)

    def match_pattern(self, pattern: 'Pattern', word: Word, start:int|None=None, stop: int|None=None, catixes: dict[int, int]={}) -> tuple[int, dict[int, int]]:
        length, catixes = self.match(word, start, stop, catixes)
        _length, catixes = super().match_pattern(pattern, word, *advance(word, length, start, stop), catixes)
        return length + _length, catixes


@dataclass(repr=False)
class Wildcard(WildcardMixin, CharacterMixin, Element):
    extended: bool

    def __str__(self) -> str:
        return ('**' if self.extended else '*') + ('' if self.greedy else '?')

    def _match(self, word: Word, index: int) -> bool:
        return self.extended or word[index] != '#'


@dataclass(repr=False)
class SubpatternMixin:
    pattern: 'Pattern'

    def match(self, word: Word, start: int|None=None, stop: int|None=None, catixes: dict[int, int]={}) -> tuple[int, dict[int, int]]:
        return self.pattern._match(word, start=start, stop=stop, catixes=catixes)


@dataclass(repr=False)
class Repetition(SubpatternMixin, Element):
    number: int

    def __str__(self) -> str:
        return f'({self.pattern}){{{self.number}}}'

    def match_pattern(self, pattern: 'Pattern', word: Word, start:int|None=None, stop: int|None=None, catixes: dict[int, int]={}) -> tuple[int, dict[int, int]]:
        length = 0
        for _ in range(self.number):
            _length, catixes = self.match(word, *advance(word, length, start, stop), catixes=catixes)
            length += _length
        _length, catixes = pattern._match(word, *advance(word, length, start, stop), catixes=catixes)
        return length + _length, catixes


@dataclass(repr=False)
class WildcardRepetition(WildcardMixin, SubpatternMixin, Element):
    def __str__(self) -> str:
        return f'({self.pattern})' + ('{*}' if self.greedy else '{*?}')


@dataclass(repr=False)
class Optional(BranchMixin, SubpatternMixin, Element):
    def __str__(self) -> str:
        return f'({self.pattern})' + ('' if self.greedy else '?')

    def _match_branch(self, pattern: 'Pattern', word: Word, start:int|None=None, stop: int|None=None, catixes: dict[int, int]={}) -> tuple[int, dict[int, int]]:
        length, catixes = self.match(word, start, stop, catixes)
        _length, catixes = pattern._match(word, *advance(word, length, start, stop), catixes)
        return length + _length, catixes


@dataclass(repr=False)
class SylBreak(Element):
    def __str__(self) -> str:
        return '$'


@dataclass(repr=False)
class Comparison(Element):
    operation: str
    value: int
    pattern: 'Pattern'

    def __str__(self) -> str:
        return f'{{{self.operation}{self.value}}}'.replace('==', '=')


@dataclass(repr=False)
class TargetRef(Element):
    direction: int

    def __str__(self) -> str:
        return '%' if self.direction == 1 else '<'


@dataclass
class Pattern:
    elements: list[Element]

    @staticmethod
    def parse(string: str, categories: dict[str, cats.Category]) -> 'Pattern':
        elements = []
        graphemes = categories.get('graphemes', ('*',))
        separator = categories.get('separator', '')
        index = 0
        _chars = ''
        while index < len(string):
            char = string[index]
            if char in '([*"%<':
                elements.extend(map(Grapheme, words.parse(_chars, graphemes, separator)))
                _chars = ''
            if char == '(':
                if string[index:index+2] == '()':
                    index += 2
                else:
                    end = match_bracket(string, index)
                    pattern = Pattern.parse(string[index+1:end], categories)
                    index = end + 1
                    if string[index:index+4] == '{*?}':
                        elements.append(WildcardRepetition(pattern, greedy=False))
                        index += 4
                    elif string[index:index+3] == '{*}':
                        elements.append(WildcardRepetition(pattern, greedy=True))
                        index += 3
                    elif string[index:index+1] == '{':
                        end = match_bracket(string, index)
                        elements.append(Repetition(pattern, int(string[index+1:end])))
                        index = end + 1
                    elif string[index:index+1] == '?':
                        elements.append(Optional(pattern, greedy=False))
                        index += 1
                    else:
                        elements.append(Optional(pattern, greedy=True))
            elif char == '[':
                if string[index:index+2] == '[]':
                    index += 2
                else:
                    end = match_bracket(string, index)
                    category = cats.Category.parse(string[index+1:end], categories)
                    index = end + 1
                    match = re.compile('[₀₁₂₃₄₅₆₇₈₉]+').match(string, index)
                    if match is None:
                        subscript = None
                    else:
                        subscript = int(match.group().translate(str.maketrans('₀₁₂₃₄₅₆₇₈₉', '0123456789')))
                        index = match.end()
                elements.append(Category(category, subscript))
            elif char == '*':
                if string[index:index+3] == '**?':
                    elements.append(Wildcard(greedy=False, extended=True))
                    index += 3
                elif string[index:index+2] == '**':
                    elements.append(Wildcard(greedy=True, extended=True))
                    index += 2
                elif string[index:index+2] == '*?':
                    elements.append(Wildcard(greedy=False, extended=False))
                    index += 2
                else:
                    elements.append(Wildcard(greedy=True, extended=False))
                    index += 1
            elif char == '"':
                elements.append(Ditto())
                index += 1
            elif char == '%':
                elements.append(TargetRef(1))
                index += 1
            elif char == '<':
                elements.append(TargetRef(-1))
                index += 1
            else:
                if char == '\\':
                    index += 1
                _chars += string[index]
                index += 1
        elements.extend(map(Grapheme, words.parse(_chars, graphemes, separator)))
        return Pattern(elements)

    def __str__(self) -> str:
        return ''.join(map(str, self.elements))

    def __repr__(self) -> str:
        return f'Pattern({str(self)!r})'

    def __bool__(self) -> bool:
        return bool(self.elements)

    def resolve(self, target: Word) -> 'Pattern':
        _target = [Grapheme(phone) for phone in target]
        _rtarget = reversed(_target)

        elements = []
        for element in self.elements:
            if isinstance(element, TargetRef):
                elements.extend(_target if element.direction == 1 else _rtarget)
            elif isinstance(element, Repetition):
                elements.append(Repetition(element.pattern.resolve(target), element.number))
            elif isinstance(element, WildcardRepetition):
                elements.append(WildcardRepetition(element.pattern.resolve(target), element.greedy))
            elif isinstance(element, Optional):
                elements.append(Optional(element.pattern.resolve(target), element.greedy))
            else:
                elements.append(element)

        return Pattern(elements)

    def as_phones(self, last_phone: str, catixes: dict[int, int]={}) -> list[str]:
        phones = []
        for elem in self.elements:
            if isinstance(elem, Grapheme):
                phones.append(elem.grapheme)
            elif isinstance(elem, Ditto):
                phones.append(phones[-1] if phones else last_phone)
            elif isinstance(elem, Category):
                if elem.subscript in catixes:
                    phones.append(elem.category[catixes[elem.subscript]])
                else:
                    raise ValueError(f'no index for category {str(elem.subscript)!r}')
            elif isinstance(elem, Repetition):
                for _ in range(elem.number):
                    phones.extend(elem.pattern.as_phones(phones[-1] if phones else last_phone, catixes))
            else:
                raise TypeError(f'cannot convert {type(elem).__name__!r} to phones')
        return phones

    def _match(self, word: Word, start: int|None=None, stop: int|None=None, catixes: dict[int, int]={}) -> tuple[int, dict[int, int]]:
        if (start is None) == (stop is None):
            raise TypeError('exactly one of start and stop must be given.')
        elif start is not None:
            iter_elements = ((element, Pattern(self.elements[i+1:])) for i, element in enumerate(self.elements))
        else:  # stop is not None
            iter_elements = ((element, Pattern(self.elements[:i])) for i, element in reversed(list(enumerate(self.elements))))

        length = 0
        for element, pattern in iter_elements:
            if hasattr(element, 'match_pattern'):
                _length, catixes = element.match_pattern(pattern, word, *advance(word, length, start, stop), catixes)
                length += _length
                break
            else:
                _length, catixes = element.match(word, *advance(word, length, start, stop), catixes)
                length += _length

        return length, catixes

    def match(self, word: Word, start: int|None=None, stop: int|None=None, catixes: dict[int, int]={}) -> tuple[slice|None, dict[int, int]]:
        try:
            length, catixes = self._match(word, start, stop, catixes)
            if start is not None:
                return Match(start, start+length), catixes
            else:  # stop is not None
                return Match(stop-length, stop), catixes
        except MatchFailed:
            return None, {}
