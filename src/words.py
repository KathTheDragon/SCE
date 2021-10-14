import re
from collections.abc import Iterator
from dataclasses import dataclass

@dataclass
class InvalidCharacter(Exception):
    char: str
    graphemes: tuple[str]
    string: str

    def __str__(self) -> str:
        return f'Encountered character {self.char!r} not in graphemes {list(self.graphemes)!r} while parsing string {self.string!r}'

@dataclass
class Word:
    phones: list[str]
    graphemes: tuple[str] = ('*',)
    separator: str = ''

    @staticmethod
    def parse(string, graphemes: tuple[str]=('*',), separator: str='') -> 'Word':
        return Word(
            phones=parse(re.sub(r'\s+', '#', f' {string} '), graphemes, separator),
            graphemes=graphemes + ('#',),
            separator=separator
        )

    def __str__(self) -> str:
        return unparse(self, self.graphemes, self.separator).strip(self.separator+'#').replace('#', ' ')

    def __len__(self) -> int:
        return len(self.phones)

    def __iter__(self) -> Iterator[str]:
        yield from self.phones

    def __getitem__(self, index: int | slice) -> 'str | Word':
        if isinstance(index, slice):
            return Word(self.phones[index], self.graphemes, self.separator)
        else:
            return self.phones[index]

def parse(string: str, graphemes: tuple[str]=('*',), separator: str='') -> list[str]:
    graphs = sorted(filter(len, graphemes), key=len, reverse=True)
    word = []
    _string = string
    string = string.lstrip(separator)
    while string:
        graph = next(filter(lambda g: startswith(string, g), graphs), None)
        if graph is None:
            raise InvalidCharacter(string[0], graphemes, _string)
        else:
            graph = string[:len(graph)]
            word.append(graph)
            string = string.removeprefix(graph).lstrip(separator)
    return word

def unparse(word: Word, graphemes: tuple[str]=('*',), separator: str='') -> str:
    string = ''
    if all(len(g) <= 1 for g in graphemes):
        string = ''.join(word)
        word = []
    ambig = []
    for graph in word:
        if ambig:
            ambig.append(graph)
            for i in range(len(ambig)):
                test = ''.join(ambig[i:])
                minlength = len(ambig[i])
                if any(startswith(test, g) and len(g) > minlength for g in graphemes):
                    string += separator
                    ambig = [graph]
                    break
            for i in range(len(ambig)):
                test = ''.join(ambig[i:])
                if any(startswith(g, test, strict=True) for g in graphemes):
                    ambig = ambig[i:]
                    break
            else:
                ambig = []
        elif any(startswith(g, graph, strict=True) for g in graphemes):
            ambig.append(graph)
        string += graph
    return string

def startswith(string: str, prefix: str, *, strict: bool=False) -> bool:
    if len(prefix) > len(string):
        return False
    elif strict and len(prefix) == len(string):
        return False
    elif '*' not in prefix and '*' not in string:
        return string.startswith(prefix)
    else:
        return all(sc == '*' or pc == '*' or sc == pc for sc, pc in zip(string, prefix))

def parseWords(words: list[str], graphemes: tuple[str]=('*',), separator: str='') -> list[Word]:
    return [Word.parse(word, graphemes, separator) for word in words]
