import re
from dataclasses import dataclass

class InvalidCharacter(Exception):
    def __init__(self, char, graphemes, string):
        self.char = char
        self.graphemes = graphemes
        self.string = string

    def __str__(self):
        return f'Encountered character {self.char!r} not in graphemes [{", ".join(self.graphemes)}] while parsing string {self.string!r}'

@dataclass
class Word:
    phones: list[str]
    graphemes: tuple[str] = ('*',)
    separator: str = ''

    @staticmethod
    def parse(string, graphemes=('*',), separator=''):
        return Word(
            phones=parse(re.sub(r'\s+', '#', f' {string} '), graphemes, separator),
            graphemes=graphemes + ('#',),
            separator=separator
        )

    def __str__(self):
        return unparse(self, self.graphemes, self.separator).replace('#', ' ').strip()

    def __iter__(self):
        yield from self.phones

def parse(string, graphemes=('*',), separator=''):
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

def unparse(word, graphemes=('*',), separator=''):
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
    return string.strip(separator+'#')

def startswith(string, prefix, *, strict=False):
    if len(prefix) > len(string):
        return False
    elif strict and len(prefix) == len(string):
        return False
    elif '*' not in prefix and '*' not in string:
        return string.startswith(prefix)
    else:
        return all(sc == '*' or pc == '*' or sc == pc for sc, pc in zip(string, prefix))

def parseWords(words, graphemes=('*',), separator=''):
    return [Word.parse(word, graphemes, separator) for word in words]
