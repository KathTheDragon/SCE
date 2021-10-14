from dataclasses import dataclass
from random import randint
from . import logger, patterns, words

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
    pattern: patterns.Pattern
    indices: list[int]

    def match(self, word: words.Word) -> list[slice]:
        matches = list(filter(None, (self.pattern.match(word, start=start) for start in range(len(word)))))
        if self.indices:
            matches = [matches[ix] for ix in self.indices if -len(matches) <= ix < len(matches)]

        if not matches:
            logger.debug('>> No matches for this target')
        elif self.pattern or self.indices:
            for match in matches:
                logger.debug(f'>> Target matched {str(word[match])!r} at {match.start}')
        else:
            logger.debug(f'>> Null target matched all positions in range 1..{len(word)}')

        return matches


@dataclass
class LocalEnvironment:
    left: patterns.Pattern
    right: patterns.Pattern

    def match(self, word: words.Word, match: slice) -> bool:
        target = word[match]
        left = self.left.resolve(target=target).match(word, stop=match.start) is not None
        right = self.right.resolve(target=target).match(word, start=match.stop) is not None
        return left and right


@dataclass
class GlobalEnvironment:
    pattern: patterns.Pattern
    indices: list[int]

    def match(self, word: words.Word, match: slice) -> bool:
        target = word[match]
        pattern = self.pattern.resolve(target=target)
        if not self.indices:
            indices = range(len(word))
        else:
            length = len(word)
            indices = ((index+length) if index < 0 else index for index in self.indices)
        return any(pattern.match(word, start=index) is not None for index in indices)

Environment = LocalEnvironment | GlobalEnvironment


def match_environments(environments: list[list[Environment]], word: words.Word, match: slice) -> bool:
    return any(all(environment.match(word, match) for environment in and_environments) for and_environments in environments)


@dataclass
class Predicate:
    result: list[patterns.Pattern]
    conditions: list[list[Environment]]
    exceptions: list[list[Environment]]

    def match(self, word: words.Word, match: slice) -> bool:
        if match_environments(self.exceptions, word, match):
            logger.debug('>> Matched an exception')
            return False
        elif match_environments(self.conditions, word, match) or not self.conditions:
            logger.debug('>> Matched a condition')
            return True
        else:
            logger.debug('>> No condition matched')
            return False


@dataclass(frozen=True)
class Flags:
    ignore: int = 0
    ditto: int = 0
    stop: int = 0
    rtl: int = 0
    repeat: int = 1
    persist: int = 1
    chance: int = 100


class _BaseRule:
    def __call__(self, word: words.Word) -> words.Word:
        if randint(1, 100) <= self.flags.chance:
            for _ in range(self.flags.repeat):
                wordin = word
                word = self._apply(word)
                if word == wordin:
                    break
        else:
            logger.info(f'{str(self)!r} was randomly not run on {str(word)!r}')
            raise RuleRandomlySkipped()
        return word


@dataclass
class Rule(_BaseRule):
    rule: str
    targets: list[Target]
    predicates: list[Predicate]
    flags: Flags = Flags()

    def __str__(self) -> str:
        return self.rule

    def _apply(self, word: words.Word) -> words.Word:
        logger.debug(f'This rule: {self}')
        logger.debug('Begin matching targets')
        matches = []
        for i, target in enumerate(self.targets):
            logger.debug(f'> Matching {str(target)!r}')
            matches.extend([(match, i) for match in target.match(word)])
        if not matches:
            logger.debug('No matches')
            logger.debug(f'{str(self)!r} does not apply to {str(word)!r}')
            raise NoMatchesFound()
        if self.flags.rtl:
            logger.debug('Sorting right-to-left')
            matches.sort(key=lambda p: (-p[0].stop, p[1]))
            def overlaps(match: slice, last_match: slice) -> bool:
                return match.stop > last_match.start
        else:
            logger.debug('Sorting left-to-right')
            matches.sort(key=lambda p: (p[0].start, p[1]))
            def overlaps(match: slice, last_match: slice) -> bool:
                return match.start < last_match.stop
        logger.debug(f'Final matches at positions {[match.start for match, _ in matches]}')

        logger.debug('Validate matches')
        changes = []
        last_match = None
        for match, i in matches:
            logger.debug(f'> Validating match at {match.start}')
            # Check overlap
            if last_match is not None and overlaps(match, last_match):
                logger.debug('>> Match overlaps with last validated match')
                continue
            for predicate in self.predicates:
                if predicate.match(word, match):
                    logger.debug('>> Match validated, getting replacement')
                    last_match = match
                    replacement = predicate.results[i % len(predicate.results)]
                    replacement = replacement.resolve(word[match])
                    logger.debug(f'>>> Replacement is {str(replacement)!r}')
                    changes.append((match, replacement))
                    break
        if not changes:
            logger.debug('No matches validated')
            logger.debug(f'{str(self)!r} does not apply to {str(word)!r}')
            raise NoMatchesValidated()
        else:
            logger.debug(f'Validated matches at {[match.start for match, _ in changes]}')

        logger.debug(f'Applying matches to {str(word)!r}')
        wordin = word
        if not self.flags.rtl:
            changes.reverse()  # We need changes to always be applied right-to-left
        for match, rep in changes:
            logger.debug(f'> Changing {str(word[match])!r} to {str(replacement)!r} at {match.start}')
            word = word.replace(match, replacement)

        logger.info(f'{str(wordin)!r} -> {str(rule)!r} -> {str(word)!r}')
        return word


@dataclass
class RuleBlock(_BaseRule):
    name: str
    rules: list
    flags: Flags = Flags()

    def __str__(self) -> str:
        return f'Block {self.name}'

    def _apply(self, word: words.Word) -> words.Word:
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
