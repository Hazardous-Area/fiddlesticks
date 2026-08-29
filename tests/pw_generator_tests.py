import string

import fiddlesticks
import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis.strategies import text

from .helpers import (
    _assert_candidate_within_M_of_pwd,
    _get_num_subs,
)

password_chars = set(string.ascii_letters + string.digits + string.punctuation)


passwords = text(
    alphabet="".join(password_chars),
    min_size=1,
    max_size=40,
)


@pytest.mark.hypothesis
@pytest.mark.slow
@given(pwd=passwords)
@settings(deadline=None, suppress_health_check=[HealthCheck.too_slow, HealthCheck.data_too_large])
def test_alt_chars_candidates_generator(pwd: str):

    M = _get_num_subs(pwd)
    _total, candidates = fiddlesticks.candidate_passwords_from_alt_chars(pwd, M)
    for candidate in candidates:
        _assert_candidate_within_M_of_pwd(candidate, pwd, M)
