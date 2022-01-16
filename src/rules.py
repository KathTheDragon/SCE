from collections.abc import Callable
from dataclasses import dataclass
from functools import reduce
from operator import and_
from random import randint
from . import logger
from .patterns import Pattern
from .words import Word

## Exceptions
class RuleDidNotApply(Exception):
    pass

class RuleRandomlySkipped(RuleDidNotApply):
    pass

class NoTargetsFound(RuleDidNotApply):
    pass

class NoTargetsValidated(RuleDidNotApply):
    pass

class BlockStopped(Exception):
    pass


## Classes
@dataclass
class Target:
    pattern: Pattern
    indices: list[int]

    def __str__(self) -> str:
        if self.indices:
            indices = '|'.join(map(str, self.indices))
            return f'{self.pattern}@{indices}'
        else:
            return str(self.pattern)

    def match(self, word: Word) -> list[tuple[slice, dict[int, int]]]:
        func = lambda i: i[0] is not None and i[0] != slice(0, 0)
        matches = list(filter(func, (self.pattern.match(word, start=start) for start in range(len(word)))))
        if self.indices:
            matches = [matches[ix] for ix in self.indices if -len(matches) <= ix < len(matches)]

        if not matches:
            logger.debug('>> Target not found')
        elif self.pattern or self.indices:
            for match, _ in matches:
                logger.debug(f'>> Found {str(word[match])!r} at {match.start}')
        else:
            logger.debug(f'>> Found null target at all positions in range 1..{len(word)}')

        return matches


@dataclass
class LocalEnvironment:
    left: Pattern
    right: Pattern

    def __str__(self) -> str:
        return f'{self.left}_{self.right}'

    def match(self, word: Word, match: slice, catixes: dict[int, int]) -> bool:
        target = word[match]
        lmatch, catixes = self.left.resolve(target).match(word, stop=match.start, catixes=catixes)
        rmatch, _ = self.right.resolve(target).match(word, start=match.stop, catixes=catixes)
        return lmatch is not None and rmatch is not None

    def match_all(self, word: Word, match: slice, catixes: dict[int, int]) -> list[int]:
        target = word[match]
        left = self.left.resolve(target)
        right = self.right.resolve(target)
        indices = []
        for index in range(len(word) + 1):
            lmatch, _catixes = left.match(word, stop=index, catixes=catixes)
            rmatch, _ = right.match(word, start=index, catixes=_catixes)
            if lmatch is not None and rmatch is not None:
                indices.append(index)
        return indices


@dataclass
class GlobalEnvironment:
    pattern: Pattern
    indices: list[int]

    def __str__(self) -> str:
        if self.indices:
            indices = '|'.join(map(str, self.indices))
            return f'{self.pattern}@{indices}'
        else:
            return str(self.pattern)

    def match(self, word: Word, match: slice, catixes: dict[int, int]) -> bool:
        target = word[match]
        pattern = self.pattern.resolve(target)
        if not self.indices:
            indices = range(len(word))
        else:
            length = len(word)
            indices = ((index+length) if index < 0 else index for index in self.indices)
        return any(pattern.match(word, start=index, catixes=catixes)[0] is not None for index in indices)

    def match_all(self, word: Word, match: slice, catixes: dict[int, int]) -> list[int]:
        # Ignoring self.pattern
        if not self.indices:
            return list(range(1, len(word)))
        else:
            length = len(word)
            return list((index+length) if index < 0 else index for index in self.indices)

Environment = LocalEnvironment | GlobalEnvironment


def match_environments(environments: list[list[Environment]], word: Word, match: slice, catixes: dict[int, int]) -> bool:
    return any(all(environment.match(word, match, catixes) for environment in and_environments) for and_environments in environments)


class Predicate:
    # conditions: list[list[Environment]]
    # exceptions: list[list[Environment]]
    def __str__(self) -> str:
        conditions = ', '.join([
            ' & '.join([str(environment) for environment in and_group])
            for and_group in self.conditions
        ])
        exceptions = ', '.join([
            ' & '.join([str(environment) for environment in and_group])
            for and_group in self.exceptions
        ])
        string = ''
        if conditions:
            string += f' / {conditions}'
        if exceptions:
            string += f' ! {exceptions}'
        return string

    def match(self, word: Word, match: slice, catixes: dict[int, int]) -> bool:
        if match_environments(self.exceptions, word, match, catixes):
            logger.debug('>>> Matched an exception')
            return False
        elif match_environments(self.conditions, word, match, catixes) or not self.conditions:
            logger.debug('>>> Matched a condition')
            return True
        else:
            logger.debug('>>> No condition matched')
            return False

    @staticmethod
    def verify(old_length: int, new_length: int) -> bool:
        return True


@dataclass
class SubstPredicate(Predicate):
    replacements: list[Pattern]
    conditions: list[list[Environment]]
    exceptions: list[list[Environment]]

    def __str__(self) -> str:
        replacements = ', '.join(map(str, self.replacements))
        return f'> {replacements}{super().__str__()}'

    def get_replacement(self, word: Word, match: slice, catixes: dict[int, int], index: int) -> list[str]:
        return (self.replacements[index % len(self.replacements)]
                .resolve(word[match])
                .as_phones(word[match.start-1], catixes))

    def get_changes(self, word: Word, match: slice, catixes: dict[int, int], index: int) -> list[tuple[slice, list[str]]]:
        return [(match, self.get_replacement(word, match, catixes, index))]


@dataclass
class InsertPredicate(Predicate):
    destinations: list[list[Environment]]
    conditions: list[list[Environment]]
    exceptions: list[list[Environment]]

    def __str__(self) -> str:
        destinations = ', '.join([
            ' & '.join([str(environment) for environment in and_group])
            for and_group in self.destinations
        ])
        return f'{destinations}{super().__str__()}'

    def get_destinations(self, word: Word, match: slice, catixes: dict[int, int], index: int) -> list[int]:
        return sorted(reduce(and_, map(lambda e: set(e.match_all(word, match, catixes)), self.destinations[index % len(self.destinations)])))

    def get_changes(self, word: Word, match: slice, catixes: dict[int, int], index: int) -> list[tuple[slice, list[str]]]:
        target = list(word[match])
        return [(slice(dest, dest), target) for dest in self.get_destinations(word, match, catixes, index)]


@dataclass
class CopyPredicate(InsertPredicate):
    def __str__(self) -> str:
        return f'>> {super().__str__()}'


@dataclass
class MovePredicate(InsertPredicate):
    def __str__(self) -> str:
        return f'-> {super().__str__()}'

    def get_changes(self, word: Word, match: slice, catixes: dict[int, int], index: int) -> list[tuple[slice, list[str]]]:
        return [(match, []), *super().get_changes(word, match, catixes, index)]

    @staticmethod
    def verify(old_length: int, new_length: int) -> bool:
        return new_length > old_length + 1


@dataclass(frozen=True)
class Flags:
    ignore: int = 0
    ditto: int = 0
    stop: int = 0
    rtl: int = 0
    repeat: int = 1
    persist: int = 1
    chance: int = 100

    def __str__(self) -> str:
        flags = []
        if self.ignore:
            flags.append('ignore')
        if self.ditto == 1:
            flags.append('ditto')
        elif self.ditto == -1:
            flags.append('!ditto')
        if self.stop == 1:
            flags.append('stop')
        elif self.stop == -1:
            flags.append('!stop')
        if self.rtl:
            flags.append('rtl')
        if self.repeat != Flags.repeat:
            flags.append(f'repeat: {self.repeat}')
        if self.persist != Flags.persist:
            flags.append(f'persist: {self.persist}')
        if self.chance != Flags.chance:
            flags.append(f'chance: {self.chance}')
        return '; '.join(flags)


class BaseRule:
    def __call__(self, word: Word) -> Word:
        if randint(1, 100) <= self.flags.chance:
            for _ in range(self.flags.repeat):
                wordin = word
                word = self._apply(word)
                if word == wordin:
                    break
            return word
        else:
            logger.info(f'{str(self)!r} was randomly not run on {str(word)!r}')
            raise RuleRandomlySkipped()


def overlaps(match1: slice, match2: slice) -> bool:
    return (match1.start < match2.start < match1.stop or
            match2.start < match1.start < match2.stop or
            match1.start == match2.start and
            (match1.start == match1.stop) == (match2.start == match2.stop))


@dataclass
class Rule(BaseRule):
    targets: list[Target]
    predicates: list[Predicate]
    flags: Flags = Flags()

    def __str__(self) -> str:
        targets = ', '.join(map(str, self.targets))
        predicates = ' '.join(map(str, self.predicates))
        return f'{targets} {predicates} {self.flags}'.strip()

    def _get_targets(self, word: Word) -> list[tuple[slice, dict[int, int], int]]:
        logger.debug('Begin finding targets')
        targets = []
        for index, target in enumerate(self.targets):
            logger.debug(f'> Searching for {str(target)!r}')
            targets.extend([(match, catixes, index) for match, catixes in target.match(word)])
        if not targets:
            logger.debug('No targets found')
            logger.debug(f'{str(self)!r} does not apply to {str(word)!r}')
            raise NoTargetsFound()
        if self.flags.rtl:
            logger.debug('Sorting right-to-left')
            targets.sort(key=lambda p: (-p[0].stop, p[2]))
        else:
            logger.debug('Sorting left-to-right')
            targets.sort(key=lambda p: (p[0].start, p[2]))
        logger.debug(f'Targets found at {", ".join([str(match.start) for match, _, _ in targets])}')
        return targets

    def _validate_targets(self, word: Word, targets: list[tuple[slice, dict[int, int], int]]) -> list[tuple[slice, dict[int, int], int, int]]:
        logger.debug('Validate targets')
        validated = []
        for match, catixes, index in targets:
            logger.debug(f'> Validating target at {match.start}')
            if validated and overlaps(match, validated[-1][0]):
                logger.debug('>> Target overlaps with last validated target')
            else:
                for pindex, predicate in enumerate(self.predicates):
                    logger.debug(f'>> Checking target against predicate {pindex + 1}')
                    if predicate.match(word, match, catixes):
                        logger.debug('>> Target validated')
                        validated.append((match, catixes, index, pindex))
                        break
                else:
                    logger.debug('>> Target failed to validate')
        if not validated:
            logger.debug('No targets validated')
            logger.debug(f'{str(self)!r} does not apply to {str(word)!r}')
            raise NoTargetsValidated()
        logger.debug(f'Validated targets at {", ".join([str(match.start) for match, _, _, _ in validated])}')
        return validated

    def _get_changes(self, word: Word, targets: list[tuple[slice, dict[int, int], int, int]]) -> list[tuple[slice, list[int]]]:
        logger.debug('Get changes')
        changes = []
        for match, catixes, index, pindex in targets:
            logger.debug(f'> Getting changes for target at {match.start}')
            _changes = changes.copy()
            predicate = self.predicates[pindex]
            for change, replacement in predicate.get_changes(word, match, catixes, index):
                if not any(overlaps(change, _change) for _change, _ in _changes):
                    _changes.append((change, replacement))
            if predicate.verify(len(changes), len(_changes)):
                changes = _changes
        return changes

    def _apply_changes(self, word: Word, changes: list[tuple[slice, list[str]]]) -> Word:
        logger.debug(f'Applying changes to {str(word)!r}')
        for match, replacement in sorted(changes, key=lambda c: (-c[0].stop, -c[0].start)):
            logger.debug(f'> Changing {str(word[match])!r} to {"".join(replacement)!r} at {match.start}')
            word = word.replace(match, replacement)
        return word

    def _apply(self, word: Word) -> Word:
        logger.debug(f'This rule: {self}')

        targets = self._get_targets(word)
        validated = self._validate_targets(word, targets)
        changes = self._get_changes(word, validated)
        newword = self._apply_changes(word, changes)

        logger.info(f'{str(word)!r} -> {str(self)!r} -> {str(newword)!r}')
        return newword


@dataclass
class RuleBlock(BaseRule):
    name: str
    rules: list[BaseRule]
    flags: Flags = Flags()

    def __str__(self) -> str:
        return f'Block {self.name}'

    def _apply(self, word: Word) -> Word:
        applied = False
        rules = []  # We use a list to store rules, since they may be applied multiple times
        values = []  # We have a parallel list for storing the values of the 'for' flag per rule
        try:
            for cur_rule in self.rules:
                # cur_rule runs before the persistent rules, but persists after them
                for rule in (cur_rule, *rules):
                    flags = rule.flags
                    if not flags.ditto or (flags.ditto != 1) ^ applied:
                        try:
                            word = rule(word)
                        except RuleDidNotApply:
                            applied = False
                        else:
                            applied = True
                        if flags.stop and (flags.stop != 1) ^ applied:
                            raise BlockStopped()
                rules.append(cur_rule)
                values.append(cur_rule.flags.persist)
                # Decrement all persistence values, discard any rules for which it reaches 0
                rules, values = zip(*[(r, v-1) for r, v in zip(rules, values) if v > 1])
        except BlockStopped:
            pass
        return word
