import itertools
import sys
from collections import defaultdict
from collections.abc import Iterator
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

import pytest
from hypothesis import HealthCheck, given, settings

from fiddlesticks import (
    IS_WINDOWS,
    SHIFT_AND_LEET_BI_MAP,
    _make_guesses_alt_chars,
)
from fiddlesticks import (
    _candidates_from_num_subs as _candidates_from_num_subs_under_test,
)
from tests.helpers import (
    passwords_guesses_first_index_and_num_subs,
)

################################################################################
# Old code to test against (i.e. for expecteds)
__version__ = "0.0.5.dev"

from fiddlesticks import (
    _calculate_total_from_alts_lengths as _calculate_total,
)


def _candidates_from_num_subs(
    guess: str,
    num_subs: int,
    alts: list[list[str]],
) -> Iterator[tuple[str, int]]:
    if num_subs == 0:
        yield guess, 0
        return
    for positions in itertools.combinations(range(len(guess)), num_subs):
        alts_at_positions = [alts[i] for i in positions if alts[i]]

        if len(alts_at_positions) != num_subs:
            continue

        for selected in itertools.product(*alts_at_positions):
            candidate_password = list(guess)
            for i, replacement in zip(positions, selected):
                candidate_password[i] = replacement
            yield "".join(candidate_password), num_subs


def _candidates_from_alts_dict(
    guesses_alts: dict[str, list[list[str]]],
    max_subs: int,
    min_subs: int = 0,
) -> Iterator[tuple[str, int]]:
    for num_subs in range(min_subs, max_subs + 1):
        # Yield candidates derived from each guess using
        # a not quite Round robin order (that restarts
        # from the earliest iterator after one is exhausted).
        iterators = [
            _candidates_from_num_subs(guess, num_subs, alts)
            for guess, alts in guesses_alts.items()
        ]
        while iterators:
            # Coverage would like to see tests covering iterators being empty,
            # which is not reachable within a while iterators: loop.
            for i, iterator in itertools.cycle(
                enumerate(iterators)
            ):  # pragma: no branch
                # More itertools' roundrobin just breaks out of the loop
                # using a next call with no fallback value, to raise StopIteration
                candidate = next(iterator, None)
                if candidate is None:
                    break
                yield candidate
            # Get rid of exhausted iterator
            iterators.pop(i)


def candidate_passwords_from_alt_chars(
    guesses: list[str],
    min_subs: int = 0,
    max_subs: int = 2,
    alt_chars: list[list[list[str]]] | None = None,
    alt_char_map: defaultdict[str, list[str]] = SHIFT_AND_LEET_BI_MAP,
) -> tuple[int, Iterator[tuple[str, int]]]:

    overrides = [None for guess in guesses] if alt_chars is None else alt_chars
    guesses_alts: dict[str, list[list[str]]]
    guesses_alts = {
        # In case alt_char_map[c] is a str
        guess: [list(alt_char_map[c]) for c in guess] if alts is None else alts
        for guess, alts in zip(guesses, overrides)
    }

    total_num_candidates = 0
    for alts in guesses_alts.values():
        lengths = [len(chars) for chars in alts]
        total_num_candidates += sum(
            _calculate_total(lengths, M) for M in range(min_subs, max_subs + 1)
        )
    candidates_it = _candidates_from_alts_dict(
        guesses_alts,
        min_subs=min_subs,
        max_subs=max_subs,
    )
    return total_num_candidates, candidates_it


#
#########################################################################


@pytest.mark.hypothesis
@pytest.mark.slow
@pytest.mark.skipif(IS_WINDOWS, reason="Only tested in CI with max_subs=10")
@given(args=passwords_guesses_first_index_and_num_subs(max_subs=10))
@settings(
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.data_too_large],
)
def test_alt_chars_candidates_generator(
    args: tuple[str, str, int, int],
):

    _pwd, guess, first_index, num_subs = args
    guess_alts = _make_guesses_alt_chars([guess], SHIFT_AND_LEET_BI_MAP)[guess]
    list_alts = [guess_alts.get(i, []) for i in range(len(guess))]

    actual_guesses_it = _candidates_from_num_subs_under_test(
        guess, num_subs, guess_alts, first_index
    )
    expected_guesses_it = _candidates_from_num_subs(guess, num_subs, list_alts)

    for _ in range(first_index):
        next(expected_guesses_it)

    for actual, expected in zip(actual_guesses_it, expected_guesses_it):
        assert actual == expected
