import sys
from contextlib import nullcontext
from datetime import datetime
from pathlib import Path

LEVELS = {
    'ERROR': 0,
    'WARN': 1,
    'INFO': 2,
    'DEBUG': 3,
}
CONSOLE = sys.stdout

file = CONSOLE
level = 'INFO'

def _open(file):
    if file is CONSOLE:
        return nullcontext(file)
    else:
        return file.open(mode='a')


def _log(level_: str, *message: str, **kwargs) -> None:
    if LEVELS[level_] > LEVELS[level]:
        return
    timestamp = datetime.now().isoformat(sep=' ', timespec='seconds')
    with _open(file) as f:
        print(timestamp, f'[{level_}]: ', end='', file=f)
        print(*message, file=f, **kwargs)


def __getattr__(name: str):
    level = name.upper()
    if level not in LEVELS:
        raise AttributeError
    def func(*message: str, **kwargs):
        _log(level, *message, **kwargs)
    func.__name__ = name
    return func
