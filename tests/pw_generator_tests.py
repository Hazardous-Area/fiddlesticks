import itertools

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis.strategies import integers

import fiddlesticks

from .helpers import (
    BI_MAP,
    _assert_candidate_within_M_of_pwds,
    _candidate_is_within_M_of_pwd,
    guesses_max_subs_and_first_index,
    passwords_guesses_and_num_subs,
    passwords_guesses_first_index_and_num_subs,
)


# Internal meta test.  Helps get 100% coverage.
@pytest.mark.parametrize(
    "guess,pwd,M,expected",
    [
        ("AA", "A", 10000, False),  # different lengths
    ],
)
def test_candidate_is_within_M_of_pwd(
    guess: str,
    pwd: str,
    M: int,
    expected: bool,
):
    assert _candidate_is_within_M_of_pwd(guess, pwd, M) == expected


@pytest.mark.hypothesis
@pytest.mark.slow
@given(password_guess_and_num_subs=passwords_guesses_and_num_subs(max_num_subs=4))
@settings(
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.data_too_large],
)
def test_alt_chars_candidates_generator(
    password_guess_and_num_subs: tuple[str, list[tuple[int, str]], int],
):
    pwd, _guess, M = password_guess_and_num_subs
    _total, candidates = fiddlesticks.candidate_passwords_from_alt_chars(
        [pwd], max_subs=M
    )
    for candidate, _num_subs in candidates:
        _assert_candidate_within_M_of_pwds(candidate, [pwd], M)


@pytest.mark.parametrize(
    "pwds",
    [
        ["ABC", "XYZ"],
        ["A", "BB", "CCC", "DDDD"],
    ],
)
def test_multiple_guesses(pwds):
    _total, candidates = fiddlesticks.candidate_passwords_from_alt_chars(
        pwds, max_subs=2
    )
    for candidate, _num_subs in candidates:
        _assert_candidate_within_M_of_pwds(candidate, pwds, 2)


def test_no_guesses():
    _total, candidates = fiddlesticks.candidate_passwords_from_alt_chars([], max_subs=2)
    assert len(list(candidates)) == 0


@pytest.mark.hypothesis
@pytest.mark.slow
@given(args=guesses_max_subs_and_first_index(max_max_subs=3, max_num_pws=4))
@settings(
    max_examples=3,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.data_too_large],
)
def test_skipping_in_candidate_passwords_from_alt_chars(
    args: tuple[list[str], int, int],
):

    guesses, max_subs, first_index = args

    actual_total, actual_guesses_it = fiddlesticks.candidate_passwords_from_alt_chars(
        guesses=guesses,
        max_subs=max_subs,
        first_index=first_index,
    )
    expected_total, expected_guesses_it = fiddlesticks.candidate_passwords_from_alt_chars(
        guesses=guesses,
        max_subs=max_subs,
        first_index=0,
    )
    for _ in range(first_index):
        next(expected_guesses_it)
    i = None
    for i, (actual, expected) in enumerate(itertools.zip_longest(actual_guesses_it, expected_guesses_it)):
        assert actual == expected


    assert (actual_total ==0 and i is None) or (i + 1 == actual_total)
    assert (expected_total == 0 and i is None) or (i + 1 + first_index == expected_total)

@pytest.mark.hypothesis
@pytest.mark.slow
@given(args=passwords_guesses_first_index_and_num_subs(max_subs=6))
@settings(
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.data_too_large],
)
def test_skipping_in_candidates_from_num_subs(
    args: tuple[str, str, int, int],
):

    _pwd, guess, first_index, num_subs = args
    guess_alts = fiddlesticks._make_guesses_alt_chars([guess], BI_MAP)[guess]

    actual_guesses_it = fiddlesticks._candidates_from_num_subs(
        guess,
        num_subs,
        guess_alts,
        first_index=first_index,
    )
    expected_guesses_it = fiddlesticks._candidates_from_num_subs(
        guess,
        num_subs,
        guess_alts,
        first_index=0,
    )
    for _ in range(first_index):
        next(expected_guesses_it)

    for actual, expected in zip(actual_guesses_it, expected_guesses_it):
        assert actual == expected


@given(first_index=integers(), num_subs=integers())
def test_trivial_round_robin_yields_nothing(first_index: int, num_subs: int):
    assert 0 == len(
        list(
            fiddlesticks._roundrobin_all_guesses(
                first_index=first_index,
                guesses_alts={},
                guesses_sub_totals={},
                num_subs=num_subs,
            )
        )
    )


@pytest.mark.parametrize(
    "guesses,num_subs,first_index,mapping,expected",
    [
        (
            [
                "3",
                "2",
                "1",
            ],
            1,
            i,
            {
                "3": ["E", "&"],
                "2": ['"'],
                "1": ["!", "l"],
            },
            [
                "E",
                '"',
                "!",
                "&",
                "l",
            ],
        )
        for i in range(5)
    ],
)
def test_round_robin_wrapping_to_next_block(
    guesses: list[str],
    num_subs: int,
    first_index: int,
    mapping: dict[str, list[str]],
    expected: list[str],
):
    guesses_alts = fiddlesticks._make_guesses_alt_chars(guesses, mapping)
    guesses_sub_totals = fiddlesticks._calculate_sub_totals(
        guesses_alts,
        min_subs=num_subs,
        max_subs=num_subs,
    )[num_subs]
    assert [(s, num_subs) for s in expected[first_index:]] == list(
        fiddlesticks._roundrobin_all_guesses(
            first_index=first_index,
            guesses_alts=guesses_alts,
            guesses_sub_totals=guesses_sub_totals,
            num_subs=num_subs,
        )
    )


@pytest.mark.parametrize(
    "guesses,max_subs,first_index,mapping,total,expected",
    [
        (
            [
                "3",
                "2",
                "1",
            ],
            1,
            3,
            {
                "3": ["E"],
                "2": ['"'],
                "1": ["!"],
            },
            6,
            [
                ("3", 0),
                ("2", 0),
                ("1", 0),
                ("E", 1),
                ('"', 1),
                ("!", 1),
            ],
        )
    ],
)
def test_candidates_from_first_index_skips_to_next_num_subs(
    guesses: list[str],
    max_subs: int,
    first_index: int,
    mapping: dict[str, list[str]],
    total: int,
    expected: list[str],
):
    guesses_alts = fiddlesticks._make_guesses_alt_chars(guesses, mapping)
    guesses_sub_totals = fiddlesticks._calculate_sub_totals(
        guesses_alts,
        max_subs=max_subs,
    )
    assert [x for x in expected[first_index:]] == list(
        fiddlesticks._candidates_from_first_index(
            first_index=first_index,
            sub_totals=guesses_sub_totals,
            guesses_alts=guesses_alts,
            total=total,
        )
    )


def test_zero_subtotals():
    # Not enough alts provided for requires minimum substitutions.
    # _calculate_sub_totals could be more proactive than
    # just returning {}, but it's 'private'.
    assert 0 == len(
        fiddlesticks._calculate_sub_totals({"a": {0: []}}, min_subs=2, max_subs=2)
    )
