from dataclasses import dataclass
from typing import overload
from . import words

class MatchFailed(Exception):
    pass

@overload
def advance(word: words.Word, length: int, start: int, stop: None) -> tuple[int, None]:
    ...
@overload
def advance(word: words.Word, length: int, start: None, stop: int) -> tuple[None, int]:
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


def get_index(word: words.Word, start: int|None=None, stop: int|None=None) -> int:
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

    def __eq__(self, other: str | Element) -> bool:
        if isinstance(other, str):
            return str(self) == other
        elif type(self) == type(other):
            return str(self) == str(other)
        else:
            return NotImplemented

    def match(self, word: words.Word, start: int|None=None, stop: int|None=None) -> int:
        if (start is None) == (stop is None):
            raise TypeError('exactly one of start and stop must be given.')
        else:
            raise MatchFailed()

class CharacterMixin:
    def _match(self, word: words.Word, index: int) -> bool:
        return False

    def match(self, word: words.Word, start: int|None=None, stop: int|None=None) -> int:
        index = get_index(word, start=start, stop=stop)
        if self._match(word, index):
            return 1
        else:
            raise MatchFailed()


@dataclass(repr=False, eq=False)
class Grapheme(CharacterMixin, Element):
    grapheme: str

    def __str__(self) -> str:
        return self.grapheme

    def _match(self, word: words.Word, index: int) -> bool:
        return word[index] == self.grapheme


@dataclass(repr=False, eq=False)
class Ditto(CharacterMixin, Element):
    def __str__(self) -> str:
        return '"'

    def _match(self, word: words.Word, index: int) -> bool:
        return index and word[index] == word[index-1]


@dataclass(repr=False, eq=False)
class Category(CharacterMixin, Element):
    category: 'cats.Category'

    def __str__(self) -> str:
        if self.category.name is None:
            return str(self.category)
        else:
            return f'[{self.category.name}]'

    def _match(self, word: words.Word, index: int) -> bool:
        return word[index] in self.category
        # Note that this will change if sequences become supported in categories
        # Somehow return the index self.category.index(word[index])


@dataclass(repr=False, eq=False)
class Wildcard(CharacterMixin, Element):
    greedy: bool
    extended: bool

    def __str__(self) -> str:
        return ('**' if self.extended else '*') + ('' if self.greedy else '?')

    def _match(self, word: words.Word, index: int) -> bool:
        return self.extended or word[index] != '#'

    def _match_pattern(self, pattern: 'Pattern', word: words.Word, start:int|None=None, stop: int|None=None) -> int:
        length = self.match(word, start=start, stop=stop)
        start, stop = advance(word, length, start=start, stop=stop)

        if self.greedy:
            try:
                return length + self._match_pattern(pattern, word, start=start, stop=stop)
            except MatchFailed:
                return length + pattern._match(word, start=start, stop=stop)
        else:
            try:
                return length + pattern._match(word, start=start, stop=stop)
            except MatchFailed:
                return length + self._match_pattern(pattern, word, start=start, stop=stop)


@dataclass(repr=False, eq=False)
class SubpatternMixin:
    pattern: 'Pattern'

    def match(self, word: words.Word, start: int|None=None, stop: int|None=None) -> int:
        return self.pattern._match(word, start=start, stop=stop)


@dataclass(repr=False, eq=False)
class Repetition(SubpatternMixin, Element):
    number: int

    def __str__(self) -> str:
        return f'{{{self.number}}}'

    def _match_pattern(self, pattern: 'Pattern', word: words.Word, start:int|None=None, stop: int|None=None) -> int:
        length = 0
        for _ in range(self.number):
            length += self.match(word, *advance(word, length, start, stop))
        return length + pattern._match(word, *advance(word, length, start, stop))


@dataclass(repr=False, eq=False)
class WildcardRepetition(SubpatternMixin, Element):
    greedy: bool

    def __str__(self) -> str:
        return '{*}' if self.greedy else '{*?}'

    def _match_pattern(self, pattern: 'Pattern', word: words.Word, start:int|None=None, stop: int|None=None) -> int:
        length = self.match(word, start=start, stop=stop)
        start, stop = advance(word, length, start=start, stop=stop)

        if self.greedy:
            try:
                return length + self._match_pattern(pattern, word, start=start, stop=stop)
            except MatchFailed:
                return length + pattern._match(word, start=start, stop=stop)
        else:
            try:
                return length + pattern._match(word, start=start, stop=stop)
            except MatchFailed:
                return length + self._match_pattern(pattern, word, start=start, stop=stop)


@dataclass(repr=False, eq=False)
class Optional(SubpatternMixin, Element):
    greedy: bool

    def __str__(self) -> str:
        return f'({self.pattern})' + ('' if self.greedy else '?')

    def _match_pattern(self, pattern: 'Pattern', word: words.Word, start:int|None=None, stop: int|None=None) -> int:
        if self.greedy:
            try:
                length = self.match(word, start=start, stop=stop)
                return length + pattern._match(word, *advance(word, length, start, stop))
            except MatchFailed:
                return pattern._match(word, start=start, stop=stop)
        else:
            try:
                return pattern._match(word, start=start, stop=stop)
            except MatchFailed:
                length = self.match(word, start=start, stop=stop)
                return length + pattern._match(word, *advance(word, length, start, stop))


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

    def resolve(self, target: words.Word|None=None) -> Pattern:
        # Will need to handle category indexing too
        if target is not None:
            target = [Grapheme(phone) for phone in target]
            rtarget = reversed(target)
            elements = []
            for element in self.elements:
                if isinstance(element, TargetRef):
                    if element == '%':
                        elements.extend(target)
                    else:
                        elements.extend(rtarget)
                else:
                    elements.append(element)
            return Pattern(elements)
        else:
            return self

    def _match(self, word: words.Word, start: int|None=None, stop: int|None=None) -> int:
        if (start is None) == (stop is None):
            raise TypeError('exactly one of start and stop must be given.')
        elif start is not None:
            length = 0
            for i, element in enumerate(self.elements):
                if hasattr(element, '_match_pattern'):
                    pattern = Pattern(self.elements[i+1:])
                    length += element._match_pattern(pattern, word, start=start+length)
                    break
                else:
                    length += element.match(word, start=start+length)

        else:  # stop is not None
            length = 0
            for i, element in reversed(list(enumerate(self.elements))):
                if hasattr(element, '_match_pattern'):
                    pattern = Pattern(self.elements[:i])
                    length += element._match_pattern(pattern, word, stop=stop-length)
                    break
                else:
                    length += element.match(word, stop=stop-length)

        return length

    def match(self, word: words.Word, start: int|None=None, stop: int|None=None) -> slice:
        try:
            length = self._match(word, start, stop)
            if start is not None:
                return Match(start, start+length)
            else:  # stop is not None
                return Match(stop-length, stop)
        except MatchFailed:
            return None
