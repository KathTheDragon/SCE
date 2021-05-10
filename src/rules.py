from dataclasses import dataclass
from random import randint

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


## Helper Functions
def match_environments(environments, word, match):
    return any(all(environment.match(word, match) for environment in and_environments) for and_environments in environments)


## Classes
@dataclass
class Target:
    pattern: 'Pattern'
    indices: list

    def match(self, word):
        matches = [match := self.pattern.match(word, start=start) for start in range(len(word)) if match is not None]
        # if not matches:
        #     debug: >> No matches for this target
        # if not self.pattern:
        #     debug: >> Null target matched all positions in range 1..{len(word)}
        # else:
        #     for match in matches:
        #         debug: >> Target matched {str(word[match.start:match.stop])!r} at {match.start}

        if not self.indices:
            return matches
        else:
            return [matches[ix] for ix in self.indices if -len(matches) <= ix < len(matches)]


@dataclass
class LocalEnvironment:
    left: 'Pattern'
    right: 'Pattern'

    def match(self, word, match):
        target = word[match.start:match.stop]
        left = self.left.resolve(target=target).match(word, stop=match.start) is not None
        right = self.right.resolve(target=target).match(word, start=match.stop) is not None
        return left and right


@dataclass
class GlobalEnvironment:
    pattern: 'Pattern'
    indices: list

    def match(self, word, match):
        target = word[match.start:match.stop]
        pattern = self.pattern.resolve(target=target)
        if not self.indices:
            indices = range(len(word))
        else:
            length = len(word)
            indices = ((index+length) if index < 0 else index for index in self.indices)
        return any(pattern.match(word, start=index) is not None for index in indices)


@dataclass
class Predicate:
    result: list
    conditions: list
    exceptions: list

    def match(self, word, match):
        if match_environments(self.exceptions, word, match):
            # debug: >> Matched an exception
            return False
        elif match_environments(self.conditions, word, match) or not self.conditions:
            # debug: >> Matched a condition
            return True
        else:
            # debug: >> No condition matched
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
    def __call__(self, word):
        if randint(1, 100) <= self.flags.chance:
            for _ in range(self.flags.repeat):
                wordin = word
                word = self._apply(word)
                if word == wordin:
                    break
        else:
            # info: {str(self)!r} was randomly not run on {str(word)!r}
            raise RuleRandomlySkipped()
        return word


@dataclass
class Rule(_BaseRule):
    rule: str
    targets: list[Target]
    predicates: list[Predicate]
    flags: Flags = Flags()

    def __str__(self):
        return self.rule

    def _apply(self, word):
        # debug: This rule: {self}
        # debug: Begin matching targets
        matches = []
        for i, target in enumerate(self.targets):
            # debug: > Matching {str(target)!r}
            matches.extend([(match, i) for match in target.match(word)])
        if not matches:
            # debug: No matches
            # debug: {str(self)!r} does not apply to {str(word)!r}
            raise NoMatchesFound()
        if self.flags.rtl:
            # debug: Sorting right-to-left
            matches.sort(key=lambda p: (-p[0].stop, p[1]))
            def overlaps(match, last_match):
                return match.stop > last_match.start
        else:
            # debug: Sorting left-to-right
            matches.sort(key=lambda p: (p[0].start, p[1]))
            def overlaps(match, last_match):
                return match.start < last_match.stop
        # debug: Final matches at positions {[match.start for match, _ in matches]}

        # debug: Validate matches
        changes = []
        last_match = None
        for match, i in matches:
            # debug: > Validating match at {match.start}
            # Check overlap
            if last_match is not None and overlaps(match, last_match):
                # debug: >> Match overlaps with last validated match
                continue
            for predicate in self.predicates:
                if predicate.match(word, match):
                    # debug: >> Match validated, getting replacement
                    last_match = match
                    replacement = predicate.results[i % len(predicate.results)]
                    replacement = replacement.resolve(match, word)
                    # debug: >>> Replacement is {str(replacement)!r}
                    changes.append((match, replacement))
                    break
        if not changes:
            # debug: No matches validated
            # debug: {str(self)!r} does not apply to {str(word)!r}
            raise NoMatchesValidated()
        # else:
        #     debug: Validated matches at {[match.start for match, _ in changes]}

        # debug: Applying matches to {str(word)!r}
        wordin = word
        if not self.flags.rtl:
            changes.reverse()  # We need changes to always be applied right-to-left
        for match, rep in changes:
            # debug: > Changing {str(word[match.start:match.stop])!r} to {str(replacement)!r} at {match.start}
            word = word.replace(match, replacement)

        # info: {str(wordin)!r} -> {str(rule)!r} -> {str(word)!r}
        return word


@dataclass
class RuleBlock(_BaseRule):
    name: str
    rules: list
    flags: Flags = Flags()

    def __str__(self):
        return f'Block {self.name}'

    def _apply(self, word):
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
