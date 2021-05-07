from dataclasses import dataclass

class MatchFailed(Exception):
    pass


@dataclass
class Match:
    start: int
    stop: int


@dataclass
class Element:
    def __str__(self):
        return ''

    def __repr__(self):
        return f'{self.type}({str(self)!r})'

    def __eq__(self, other):
        if isinstance(other, str):
            return str(self) == other
        elif type(self) == type(other):
            return str(self) == str(other)
        else:
            return NotImplemented

    def get_index(self, word, start=None, stop=None):
        if (start is None) == (stop is None):
            raise TypeError('exactly one of start and stop must be given.')
        elif start is None:
            if stop <= 0:
                raise MatchFailed()
            return stop - 1
        else:  # stop is None
            if start >= len(word):
                raise MatchFailed()
            return start

    # Returns the length of the match; -1 denotes no match
    def match(self, word, start=None, stop=None):
        if (start is None) == (stop is None):
            raise TypeError('exactly one of start and stop must be given.')
        else:
            raise MatchFailed()


@dataclass(repr=False, eq=False)
class Grapheme(Element):
    grapheme: str

    def __str__(self):
        return self.grapheme

    def match(self, word, start=None, stop=None):
        index = self.get_index(word, start, stop)
        if word[index] == self.grapheme:
            length = 1
            if start is None:
                return None, stop - length
            else:
                return start + length, None
        else:
            raise MatchFailed()


@dataclass(repr=False, eq=False)
class Ditto(Element):
    def __str__(self):
        return '"'

    def match(self, word, start=None, stop=None):
        index = self.get_index(word, start, stop)
        if index and word[index] == word[index-1]:
            length = 1
            if start is None:
                return None, stop - length
            else:
                return start + length, None
        else:
            raise MatchFailed()


@dataclass(repr=False, eq=False)
class Category(Element):
    category: 'cats.Category'

    def __str__(self):
        if self.category.name is None:
            return str(self.category)
        else:
            return f'[{self.category.name}]'

    def match(self, word, start=None, stop=None):
        index = self.get_index(word, start, stop)
        if word[index] in self.category:
            length = 1
            # Note that this 1 will change if sequences become supported in categories
            if start is None:
                return None, stop - length
            else:
                return start + length, None
            # Somehow return the index self.category.index(word[index])
        else:
            raise MatchFailed()


@dataclass(repr=False, eq=False)
class Wildcard(Element):
    greedy: bool
    extended: bool

    def __str__(self):
        return ('**' if self.extended else '*') + ('' if self.greedy else '?')

    def match(self, word, start=None, stop=None):
        index = self.get_index(word, start, stop)
        if self.extended or word[index] != '#':
            length = 1
            if start is None:
                return None, stop - length
            else:
                return start + length, None
        else:
            raise MatchFailed()

    def _match_pattern(self, pattern, word, start=None, stop=None):
        start, stop = self.match(word, start=start, stop=stop)

        if self.greedy:
            try:
                return self._match_pattern(pattern, word, start=start, stop=stop)
            except MatchFailed:
                return pattern._match(word, start=start, stop=stop)
        else:
            try:
                return pattern._match(word, start=start, stop=stop)
            except MatchFailed:
                return self._match_pattern(pattern, word, start=start, stop=stop)


@dataclass(repr=False, eq=False)
class Repetition(Element):
    number: int
    pattern: 'Pattern'

    def __str__(self):
        return f'{{{self.number}}}'

    def match(self, word, start=None, stop=None):
        if (start is None) == (stop is None):
            raise TypeError('exactly one of start and stop must be given.')
        elif start is None:
            index = stop
            for _ in range(self.number):
                index = self.pattern._match(word, stop=index).start
            return None, index
        else:  # stop is None
            index = start
            for _ in range(self.number):
                index = self.pattern._match(word, start=index).stop
            return index, None


@dataclass(repr=False, eq=False)
class WildcardRepetition(Element):
    greedy: bool
    pattern: 'Pattern'

    def __str__(self):
        return '{*}' if self.greedy else '{*?}'

    def match(self, word, start=None, stop=None):
        match = self.pattern._match(word, start=start, stop=stop)
        if start is None:
            return None, match.start
        else:
            return match.stop, None

    def _match_pattern(self, pattern, word, start=None, stop=None):
        start, stop = self.match(word, start=start, stop=stop)

        if self.greedy:
            try:
                return self._match_pattern(pattern, word, start=start, stop=stop)
            except MatchFailed:
                return pattern._match(word, start=start, stop=stop)
        else:
            try:
                return pattern._match(word, start=start, stop=stop)
            except MatchFailed:
                return self._match_pattern(pattern, word, start=start, stop=stop)


@dataclass(repr=False, eq=False)
class Optional(Element):
    greedy: bool
    pattern: 'Pattern'

    def __str__(self):
        return f'({self.pattern})' + ('' if self.greedy else '?')

    def match(self, word, start=None, stop=None):
        match = self.pattern._match(word, start=start, stop=stop)
        if start is None:
            return None, match.start
        else:
            return match.stop, None

    def _match_pattern(self, pattern, word, start=None, stop=None):
        if self.greedy:
            try:
                _start, _stop = self.match(word, start=start, stop=stop)
                return pattern._match(word, start=_start, stop=_stop)
            except MatchFailed:
                return pattern._match(word, start=start, stop=stop)
        else:
            try:
                return pattern._match(word, start=start, stop=stop)
            except MatchFailed:
                start, stop = self.match(word, start=start, stop=stop)
                return pattern._match(word, start=start, stop=stop)


@dataclass(repr=False, eq=False)
class TargetRef(Element):
    direction: int

    def __str__(self):
        return '%' if self.direction == 1 else '<'


@dataclass
class Pattern:
    elements: list[Element]

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
        elif start is None:
            index = stop
            for i, element in reversed(enumerate(self.elements)):
                if isinstance(element, (Optional, Wildcard, WildcardRepetition)):
                    pattern = Pattern(self.elements[:i])
                    index = element._match_pattern(pattern, word, stop=index).start
                    break

                _, index = element.match(word, stop=index)

            return Match(index, stop)

        else:  # stop is None
            index = start
            for i, element in enumerate(self.elements):
                if isinstance(element, (Optional, Wildcard, WildcardRepetition)):
                    pattern = Pattern(self.elements[i+1:])
                    index = element._match_pattern(pattern, word, start=index).stop
                    break

                index, _ = element.match(word, start=index)

            return Match(start, index)

    def match(self, word, start=None, stop=None):
        try:
            return self._match(word, start, stop)
        except MatchFailed:
            return None

    def matchall(self, word, start=None, stop=None):
        matches = []
        for start in range(slice(start, stop).indices(len(word))):
            match = self.match(word, start=start)
            if match is not None:
                matches.append(match)
        return matches
