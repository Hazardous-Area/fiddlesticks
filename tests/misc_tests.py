from unittest.mock import patch

import pytest

from fiddlesticks import (
    IS_WINDOWS,
    _get_hopefully_incorrect_password,
    cli,
    possibly_output_found_password,
)

from .helpers import (
    SEVEN_ZIP_TEST_ARCHIVE,
    _assert_output_on_found_password,
)


@pytest.mark.skipif(
    IS_WINDOWS, reason="I haven't figured out the 7zip CLI on Windows yet"
)
def test_password_from_getpass_in_CLI(capsys):
    with patch("getpass.getpass", side_effect=["test", ""]):
        assert 0 == cli(["--max-subs", "0", str(SEVEN_ZIP_TEST_ARCHIVE)])
    capsys.readouterr()


def test_get_hopefully_incorrect_password_username_not_found(capsys):
    with patch("getpass.getuser", side_effect=OSError):
        assert "password123" == _get_hopefully_incorrect_password()


@pytest.mark.parametrize(
    "print_passwords",
    [True, False],
)
def test_possibly_output_found_password_no_time(
    print_passwords: bool,
    capsys,
):
    password = "abcde"
    i = 5
    # This currently only gets called without a calculation time
    # if the password was the user's username, or "password123",
    # when using an SSH key password checker.
    possibly_output_found_password(
        password=password,
        i=i,
        t=None,
        print_passwords=print_passwords,
    )

    stdout, stderr = capsys.readouterr()
    _assert_output_on_found_password(password, i, print_passwords, stdout, stderr)
