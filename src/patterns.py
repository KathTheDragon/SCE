from dataclasses import dataclass

class MatchFailed(Exception):
    pass


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


def get_index(word, start=None, stop=None):
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


@dataclass
class Match:
    start: int
    stop: int


@dataclass
class Element:
    def __str__(self):
        return ''

    def __repr__(self):
        return f'{self.__class__.__name__}({str(self)!r})'

    def __eq__(self, other):
        if isinstance(other, str):
            return str(self) == other
        elif type(self) == type(other):
            return str(self) == str(other)
        else:
            return NotImplemented

    def match(self, word, start=None, stop=None):
        if (start is None) == (stop is None):
            raise TypeError('exactly one of start and stop must be given.')
        else:
            raise MatchFailed()

class CharacterMixin:
    def _match(self, word, index):
        return False

    def match(self, word, start=None, stop=None):
        index = get_index(word, start=start, stop=stop)
        if self._match(word, index):
            return 1
        else:
            raise MatchFailed()


@dataclass(repr=False, eq=False)
class Grapheme(CharacterMixin, Element):
    grapheme: str

    def __str__(self):
        return self.grapheme

    def _match(self, word, index):
        return word[index] == self.grapheme


@dataclass(repr=False, eq=False)
class Ditto(CharacterMixin, Element):
    def __str__(self):
        return '"'

    def _match(self, word, index):
        return index and word[index] == word[index-1]


@dataclass(repr=False, eq=False)
class Category(CharacterMixin, Element):
    category: 'cats.Category'

    def __str__(self):
        if self.category.name is None:
            return str(self.category)
        else:
            return f'[{self.category.name}]'

    def _match(self, word, index):
        return word[index] in self.category
        # Note that this will change if sequences become supported in categories
        # Somehow return the index self.category.index(word[index])


@dataclass(repr=False, eq=False)
class Wildcard(CharacterMixin, Element):
    greedy: bool
    extended: bool

    def __str__(self):
        return ('**' if self.extended else '*') + ('' if self.greedy else '?')

    def _match(self, word, index):
        return self.extended or word[index] != '#'

    def _match_pattern(self, pattern, word, start=None, stop=None):
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

    def match(self, word, start=None, stop=None):
        return self.pattern._match(word, start=start, stop=stop)


@dataclass(repr=False, eq=False)
class Repetition(SubpatternMixin, Element):
    number: int

    def __str__(self):
        return f'{{{self.number}}}'

    def _match_pattern(self, pattern, word, start=None, stop=None):
        length = 0
        for _ in range(self.number):
            length += self.match(word, *advance(word, length, start, stop))
        return length + pattern._match(word, *advance(word, length, start, stop))


@dataclass(repr=False, eq=False)
class WildcardRepetition(SubpatternMixin, Element):
    greedy: bool

    def __str__(self):
        return '{*}' if self.greedy else '{*?}'

    def _match_pattern(self, pattern, word, start=None, stop=None):
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

    def __str__(self):
        return f'({self.pattern})' + ('' if self.greedy else '?')

    def _match_pattern(self, pattern, word, start=None, stop=None):
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

    def __str__(self):
        return '%' if self.direction == 1 else '<'


@dataclass
class Pattern:
    elements: list[Element]

    def __str__(self):
        return ''.join(map(str, self.elements))

    def __repr__(self):
        return f'Pattern({str(self)!r})'

    def resolve(self, target=None):
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

    def _match(self, word, start=None, stop=None):
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
            for i, element in reversed(enumerate(self.elements)):
                if hasattr(element, '_match_pattern'):
                    pattern = Pattern(self.elements[:i])
                    length += element._match_pattern(pattern, word, stop=stop-length)
                    break
                else:
                    length += element.match(word, stop=stop-length)

        return length

    def match(self, word, start=None, stop=None):
        try:
            length = self._match(word, start, stop)
            if start is not None:
                return Match(start, start+length)
            else:  # stop is not None
                return Match(stop-length, stop)
        except MatchFailed:
            return None

    def matchall(self, word, start=None, stop=None):
        matches = []
        for start in range(slice(start, stop).indices(len(word))):
            match = self.match(word, start=start)
            if match is not None:
                matches.append(match)
        return matches
