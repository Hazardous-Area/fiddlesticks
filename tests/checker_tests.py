import subprocess

import pytest

from .helpers import (
    avdu_test_vault,
    IS_WINDOWS,
)

from fiddlesticks import make_py_avdu_aegis_checker


@pytest.mark.skipif(IS_WINDOWS, reason="I haven't figured out the 7zip CLI on Windows yet")
def test_is_7zip_installed():
    args = ["7z", "--help"]
    subprocess.check_call(args)


def test_aegis_checker_against_avdu_vault(avdu_test_vault):
    checker = make_py_avdu_aegis_checker(avdu_test_vault)
    # """
    # # Run using the encrypted test file. (Enter password "test" when prompted.)
    # go run ./cmd/avdu -p test/data/aegis_encrypted.json -e
    # https://github.com/Sammy-T/avdu/blob/master/README.md
    # """
    assert checker("test")
    assert not checker("not_test")
