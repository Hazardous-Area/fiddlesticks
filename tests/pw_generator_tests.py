import pytest
from hypothesis import HealthCheck, given, settings

import fiddlesticks

from .helpers import (
    _assert_candidate_within_M_of_pwds,
    _candidate_is_within_M_of_pwd,
    passwords_guesses_and_num_subs,
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
    pwd, _guesses, M = password_guess_and_num_subs
    _total, candidates = fiddlesticks.candidate_passwords_from_alt_chars([pwd], M)
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
    _total, candidates = fiddlesticks.candidate_passwords_from_alt_chars(pwds, 2)
    for candidate, _num_subs in candidates:
        _assert_candidate_within_M_of_pwds(candidate, pwds, 2)
