def find(string: str, *substrings: str, start: int=0, stop: int=-1, error_msg: str='') -> int:
    """Nesting-aware substring finder."""

    if stop < 0:
        stop = len(string)
    if not error_msg:
        error_msg = 'does not have an opening bracket in the given range'
    index = start
    while index < stop:
        for substring in substrings:
            if string[index:].startswith(substring):
                return index
        else:
            char = string[index]
            if char == '\\':
                index += 2
            elif char in '([{':
                index = match_bracket(string, index) + 1
            elif char in ')]}':
                raise ValueError(f'{char!r} at {index} {error_msg}')
            else:
                index += 1
    return -1


def contains(string: str, *substrings: str) -> bool:
    """Nesting-aware substring detector."""

    index = find(string, *substrings, error_msg='does not have an opening bracket')
    return index != -1


def match_bracket(string: str, start: int) -> int:
    """Nesting-aware bracket matcher."""

    open = string[start]
    if open == '(':
        close = ')'
    elif open == '[':
        close = ']'
    elif open == '{':
        close = '}'
    else:
        raise ValueError(f'{open!r} is not a bracket')
    index = find(string, close, start=start + 1, error_msg=f'does not match {open!r} at {start}')
    if index != -1:
        return index
    else:
        raise ValueError(f'{open!r} at {start} does not have a closing bracket')


def split(string: str, *separators: str, keep_separators: bool=False) -> list[str]:
    """Nesting-aware string splitter."""

    parts = []
    start = 0
    while True:
        index = find(string, *separators, start=start, error_msg='does not have an opening bracket')
        if index != -1:
            parts.append(string[:index])
            string = string[index:]
            for separator in separators:
                if string.startswith(separator):
                    if keep_separators:
                        start = len(separator)
                    else:
                        string = string.removeprefix(separator)
                    break
        else:
            parts.append(string)
            break
    return parts
