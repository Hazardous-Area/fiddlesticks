import subprocess

import pytest

from fiddlesticks import make_py_avdu_aegis_checker, make_pykeepass_checker

from .helpers import (
    IS_WINDOWS,
    KDBX_TEST_VAULT,
    avdu_test_vault,  # noqa: F401
)


@pytest.mark.skipif(IS_WINDOWS, reason="I haven't figured out the 7zip CLI on Windows yet")
def test_is_7zip_installed():
    args = ["7z", "--help"]
    subprocess.check_call(args)


def test_aegis_checker_against_avdu_vault(avdu_test_vault):  # noqa: F811
    checker = make_py_avdu_aegis_checker(avdu_test_vault)
    # """
    # # Run using the encrypted test file. (Enter password "test" when prompted.)
    # go run ./cmd/avdu -p test/data/aegis_encrypted.json -e
    # https://github.com/Sammy-T/avdu/blob/master/README.md
    # """
    assert checker("test")
    assert not checker("wrong_password")

def test_pykeepass_checker_against_Test_vault():
    checker = make_pykeepass_checker(KDBX_TEST_VAULT)
    assert checker("test")
    assert not checker("wrong_password")
