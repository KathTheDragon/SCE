from dataclasses import dataclass
from typing import overload
from .words import Word

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

    def __eq__(self, other: 'str | Element') -> bool:
        if isinstance(other, str):
            return str(self) == other
        elif type(self) == type(other):
            return str(self) == str(other)
        else:
            return NotImplemented

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


@dataclass(repr=False, eq=False)
class Grapheme(CharacterMixin, Element):
    grapheme: str

    def __str__(self) -> str:
        return self.grapheme

    def _match(self, word: Word, index: int) -> bool:
        return word[index] == self.grapheme


@dataclass(repr=False, eq=False)
class Ditto(CharacterMixin, Element):
    def __str__(self) -> str:
        return '"'

    def _match(self, word: Word, index: int) -> bool:
        return index and word[index] == word[index-1]


@dataclass(repr=False, eq=False)
class Category(Element):
    category: 'cats.Category'
    subscript: int | None

    def __str__(self) -> str:
        if self.category.name is None:
            return str(self.category)
        else:
            return f'[{self.category.name}]'

    def match(self, word: Word, start: int|None=None, stop: int|None=None, catixes: dict[int, int]={}) -> tuple[int, dict[int, int]]:
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


@dataclass(repr=False, eq=False)
class Wildcard(CharacterMixin, Element):
    greedy: bool
    extended: bool

    def __str__(self) -> str:
        return ('**' if self.extended else '*') + ('' if self.greedy else '?')

    def _match(self, word: Word, index: int) -> bool:
        return self.extended or word[index] != '#'

    def _match_pattern(self, pattern: 'Pattern', word: Word, start:int|None=None, stop: int|None=None, catixes: dict[int, int]={}) -> tuple[int, dict[int, int]]:
        length, catixes = self.match(word, start=start, stop=stop, catixes=catixes)
        start, stop = advance(word, length, start=start, stop=stop)

        if self.greedy:
            try:
                _length, catixes = self._match_pattern(pattern, word, start=start, stop=stop, catixes=catixes)
            except MatchFailed:
                _length, catixes = pattern._match(word, start=start, stop=stop, catixes=catixes)
        else:
            try:
                _length, catixes = pattern._match(word, start=start, stop=stop, catixes=catixes)
            except MatchFailed:
                _length, catixes = self._match_pattern(pattern, word, start=start, stop=stop, catixes=catixes)
        return length + _length, catixes


@dataclass(repr=False, eq=False)
class SubpatternMixin:
    pattern: 'Pattern'

    def match(self, word: Word, start: int|None=None, stop: int|None=None, catixes: dict[int, int]={}) -> tuple[int, dict[int, int]]:
        return self.pattern._match(word, start=start, stop=stop, catixes=catixes)


@dataclass(repr=False, eq=False)
class Repetition(SubpatternMixin, Element):
    number: int

    def __str__(self) -> str:
        return f'({self.pattern}){{{self.number}}}'

    def _match_pattern(self, pattern: 'Pattern', word: Word, start:int|None=None, stop: int|None=None, catixes: dict[int, int]={}) -> tuple[int, dict[int, int]]:
        length = 0
        for _ in range(self.number):
            _length, catixes = self.match(word, *advance(word, length, start, stop), catixes=catixes)
            length += _length
        _length, catixes = pattern._match(word, *advance(word, length, start, stop), catixes=catixes)
        return length + _length, catixes


@dataclass(repr=False, eq=False)
class WildcardRepetition(SubpatternMixin, Element):
    greedy: bool

    def __str__(self) -> str:
        return f'({self.pattern})' + ('{*}' if self.greedy else '{*?}')

    def _match_pattern(self, pattern: 'Pattern', word: Word, start:int|None=None, stop: int|None=None, catixes: dict[int, int]={}) -> tuple[int, dict[int, int]]:
        length, catixes = self.match(word, start=start, stop=stop, catixes=catixes)
        start, stop = advance(word, length, start=start, stop=stop)

        if self.greedy:
            try:
                _length, catixes = self._match_pattern(pattern, word, start=start, stop=stop, catixes=catixes)
            except MatchFailed:
                _length, catixes = pattern._match(word, start=start, stop=stop, catixes=catixes)
        else:
            try:
                _length, catixes = pattern._match(word, start=start, stop=stop, catixes=catixes)
            except MatchFailed:
                _length, catixes = self._match_pattern(pattern, word, start=start, stop=stop, catixes=catixes)
        return length + _length, catixes


@dataclass(repr=False, eq=False)
class Optional(SubpatternMixin, Element):
    greedy: bool

    def __str__(self) -> str:
        return f'({self.pattern})' + ('' if self.greedy else '?')

    def _match_pattern(self, pattern: 'Pattern', word: Word, start:int|None=None, stop: int|None=None, catixes: dict[int, int]={}) -> tuple[int, dict[int, int]]:
        if self.greedy:
            try:
                length, _catixes = self.match(word, start=start, stop=stop, catixes=catixes)
                _length, _catixes = pattern._match(word, *advance(word, length, start, stop), catixes=_catixes)
                return length + _length, _catixes
            except MatchFailed:
                return pattern._match(word, start=start, stop=stop, catixes=catixes)
        else:
            try:
                return pattern._match(word, start=start, stop=stop, catixes=catixes)
            except MatchFailed:
                length, _catixes = self.match(word, start=start, stop=stop, catixes=catixes)
                _length, _catixes = pattern._match(word, *advance(word, length, start, stop), catixes=_catixes)
                return length + _length, _catixes


@dataclass(repr=False, eq=False)
class TargetRef(Element):
    direction: int

    def __str__(self) -> str:
        return '%' if self.direction == 1 else '<'


@dataclass
class Pattern:
    elements: list[Element]

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
                elements.extend(_target if element == '%' else _rtarget)
            elif isinstance(element, Repetition):
                elements.append(Repetition(element.pattern.resolve(target), element.number))
            elif isinstance(element, WildcardRepetition):
                elements.append(WildcardRepetition(element.pattern.resolve(target), element.greedy))
            elif isinstance(element, Optional):
                elements.append(Optional(element.pattern.resolve(target), element.greedy))
            else:
                elements.append(element)

        return Pattern(elements)

    def as_phones(self, last_phone: str):
        phones = []
        for elem in self.elements:
            if isinstance(elem, Grapheme):
                phones.append(elem.grapheme)
            elif isinstance(elem, Ditto):
                phones.append(phones[-1] if phones else last_phone)
            elif isinstance(elem, Repetition):
                for _ in range(elem.number):
                    phones.extend(elem.pattern.as_phones(phones[-1] if phones else last_phone))
            else:
                raise TypeError(f'cannot convert {type(elem).__name__!r} to phones')
        return phones

    def _match(self, word: Word, start: int|None=None, stop: int|None=None, catixes: dict[int, int]={}) -> tuple[int, dict[int, int]]:
        if (start is None) == (stop is None):
            raise TypeError('exactly one of start and stop must be given.')
        elif start is not None:
            length = 0
            for i, element in enumerate(self.elements):
                if hasattr(element, '_match_pattern'):
                    pattern = Pattern(self.elements[i+1:])
                    _length, catixes = element._match_pattern(pattern, word, start=start+length, catixes=catixes)
                    length += _length
                    break
                else:
                    _length, catixes = element.match(word, start=start+length, catixes=catixes)
                    length += _length

        else:  # stop is not None
            length = 0
            for i, element in reversed(list(enumerate(self.elements))):
                if hasattr(element, '_match_pattern'):
                    pattern = Pattern(self.elements[:i])
                    _length, catixes = element._match_pattern(pattern, word, stop=stop-length, catixes=catixes)
                    length += _length
                    break
                else:
                    _length, catixes = element.match(word, stop=stop-length, catixes=catixes)
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
