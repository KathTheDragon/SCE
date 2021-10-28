from collections.abc import Callable
from dataclasses import dataclass
from random import randint
from . import logger
from .patterns import Pattern
from .words import Word

## Exceptions
class RuleDidNotApply(Exception):
    pass

class RuleRandomlySkipped(RuleDidNotApply):
    pass

class NoMatchesFound(RuleDidNotApply):
    pass

class NoMatchesValidated(RuleDidNotApply):
    pass

class BlockStopped(Exception):
    pass


## Classes
@dataclass
class Target:
    pattern: Pattern
    indices: list[int]

    def match(self, word: Word) -> list[tuple[slice, dict[int, int]]]:
        func = lambda i: i[0] is not None and i[0] != slice(0, 0)
        matches = list(filter(func, (self.pattern.match(word, start=start) for start in range(len(word)))))
        if self.indices:
            matches = [matches[ix] for ix in self.indices if -len(matches) <= ix < len(matches)]

        if not matches:
            logger.debug('>> No matches for this target')
        elif self.pattern or self.indices:
            for match, _ in matches:
                logger.debug(f'>> Target matched {str(word[match])!r} at {match.start}')
        else:
            logger.debug(f'>> Null target matched all positions in range 1..{len(word)}')

        return matches


@dataclass
class LocalEnvironment:
    left: Pattern
    right: Pattern

    def match(self, word: Word, match: slice, catixes: dict[int, int]) -> bool:
        target = word[match]
        lmatch, catixes = self.left.resolve(target).match(word, stop=match.start, catixes=catixes)
        rmatch, _ = self.right.resolve(target).match(word, start=match.stop, catixes=catixes)
        return lmatch is not None and rmatch is not None


@dataclass
class GlobalEnvironment:
    pattern: Pattern
    indices: list[int]

    def match(self, word: Word, match: slice, catixes: dict[int, int]) -> bool:
        target = word[match]
        pattern = self.pattern.resolve(target)
        if not self.indices:
            indices = range(len(word))
        else:
            length = len(word)
            indices = ((index+length) if index < 0 else index for index in self.indices)
        return any(pattern.match(word, start=index, catixes=catixes)[0] is not None for index in indices)

Environment = LocalEnvironment | GlobalEnvironment


def match_environments(environments: list[list[Environment]], word: Word, match: slice, catixes: dict[int, int]) -> bool:
    return any(all(environment.match(word, match, catixes) for environment in and_environments) for and_environments in environments)


@dataclass
class Predicate:
    replacements: list[Pattern]
    conditions: list[list[Environment]]
    exceptions: list[list[Environment]]

    def match(self, word: Word, match: slice, catixes: dict[int, int]) -> bool:
        if match_environments(self.exceptions, word, match, catixes):
            logger.debug('>> Matched an exception')
            return False
        elif match_environments(self.conditions, word, match, catixes) or not self.conditions:
            logger.debug('>> Matched a condition')
            return True
        else:
            logger.debug('>> No condition matched')
            return False



    def get_replacement(self, word: Word, match: slice, catixes: dict[int, int], index: int) -> list[str] | None:
        if self.match(word, match, catixes):
            return (self.replacements[index % len(self.replacements)]
                    .resolve(word[match])
                    .as_phones(word[match.start-1], catixes))
        else:
            return None
@dataclass(frozen=True)
class Flags:
    ignore: int = 0
    ditto: int = 0
    stop: int = 0
    rtl: int = 0
    repeat: int = 1
    persist: int = 1
    chance: int = 100


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


@dataclass
class Rule(BaseRule):
    rule: str
    targets: list[Target]
    predicates: list[Predicate]
    flags: Flags = Flags()

    def __str__(self) -> str:
        return self.rule

    def _get_matches(self, word: Word) -> list[tuple[slice, dict[int, int], int]]:
        logger.debug('Begin matching targets')
        matches = []
        for i, target in enumerate(self.targets):
            logger.debug(f'> Matching {str(target)!r}')
            matches.extend([(match, catixes, i) for match, catixes in target.match(word)])
        if not matches:
            logger.debug('No matches')
            logger.debug(f'{str(self)!r} does not apply to {str(word)!r}')
            raise NoMatchesFound()
        if self.flags.rtl:
            logger.debug('Sorting right-to-left')
            matches.sort(key=lambda p: (-p[0].stop, p[2]))
        else:
            logger.debug('Sorting left-to-right')
            matches.sort(key=lambda p: (p[0].start, p[2]))
        logger.debug(f'Final matches at positions {[match.start for match, _, _ in matches]}')
        return matches

    def _validate_matches(self, word: Word, matches: list[tuple[slice, dict[int, int], int]]) -> list[tuple[slice, list[str]]]:
        logger.debug('Validate matches')
        changes = []
        if self.flags.rtl:
            def overlaps(match: slice, last_match: slice) -> bool:
                return match.stop > last_match.start
        else:
            def overlaps(match: slice, last_match: slice) -> bool:
                return match.start < last_match.stop
        for match, catixes, i in matches:
            logger.debug(f'> Validating match at {match.start}')
            # Check overlap
            if changes and overlaps(match, changes[-1][0]):
                logger.debug('>> Match overlaps with last validated match')
            else:
                for predicate in self.predicates:
                    replacement = predicate.get_replacement(word, match, catixes, i)
                    if replacement is not None:
                        logger.debug(f'>> Match validated, replacement is {"".join(replacement)!r}')
                        changes.append((match, replacement))
                        break
        if not changes:
            logger.debug('No matches validated')
            logger.debug(f'{str(self)!r} does not apply to {str(word)!r}')
            raise NoMatchesValidated()
        else:
            logger.debug(f'Validated matches at {[match.start for match, _ in changes]}')
            return changes

    def _apply_changes(self, word: Word, changes: list[tuple[slice, list[str]]]) -> Word:
        logger.debug(f'Applying matches to {str(word)!r}')
        if not self.flags.rtl:
            changes.reverse()  # We need changes to always be applied right-to-left
        for match, replacement in changes:
            logger.debug(f'> Changing {str(word[match])!r} to {"".join(replacement)!r} at {match.start}')
            word = word.replace(match, replacement)
        return word

    def _apply(self, word: Word) -> Word:
        logger.debug(f'This rule: {self}')
        wordin = word

        matches = self._get_matches(word)
        changes = self._validate_matches(word, matches)
        word = self._apply_changes(word, changes)

        logger.info(f'{str(wordin)!r} -> {str(rule)!r} -> {str(word)!r}')
        return word


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
        wordin = word
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
