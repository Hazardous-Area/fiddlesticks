import io
from pathlib import Path
from unittest.mock import patch

import msoffcrypto
import msoffcrypto.exceptions
import pytest
from cryptography.hazmat.primitives.serialization import (
    load_pem_private_key,
    load_ssh_private_key,
)

from fiddlesticks import (
    IS_WINDOWS,
    _get_hopefully_incorrect_password,
    cli,
    possibly_output_found_password,
)

from .helpers import (
    DOCX_FILE,
    SEVEN_ZIP_TEST_ARCHIVE,
    XLSX_FILE,
    _assert_output_on_found_password,
    _try_make_ssh_key_files,
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


def test_are_error_strings_in_cryptography_unchanged(tmp_path):
    keyfiles_and_pwds = _try_make_ssh_key_files(tmp_path, "testtesttest")
    n = 0
    for error_str, loader, file in [
        (
            "Corrupt data: broken checksum",
            load_ssh_private_key,
            keyfiles_and_pwds[-1][0],
        ),
        (
            "Incorrect password, could not decrypt key",
            load_pem_private_key,
            keyfiles_and_pwds[1][0],
        ),
        # Seen other errors:
        #
        #         3
        # =================================== FAILURES ===================================
        # _______________ test_are_error_strings_in_cryptography_unchanged _______________
        # tests/misc_tests.py:78: in test_are_error_strings_in_cryptography_unchanged
        #     loader(private_key_data, ***"the_wrong_password")
        # E   ValueError: Could not deserialize key data. The data may be in an incorrect format, it may be encrypted with an unsupported algorithm, or it may be an unsupported key type (e.g. EC curves with explicit parameters). Details: ASN.1 parsing error: unexpected tag (got Tag { value: 20, constructed: false, class: Application })
        # E   If your key is in PKCS#8 format, you must use BEGIN/END PRIVATE KEY PEM delimiters
        #
        # https://github.com/Hazardous-Area/fiddlesticks/actions/runs/33859787867/job/100981355309#logs
    ]:
        private_key_data = file.read_bytes()
        try:
            loader(private_key_data, password=b"the_wrong_password")
        except ValueError as e:
            assert e.args[0] == error_str, (
                "The error string in the Cryptography dependency has changed. "
            )
            n += 1

    assert n == 2, (
        "SSH Key file loaded via cryptography primitive with the_wrong_password??!!"
    )


@pytest.mark.parametrize("path", [XLSX_FILE, DOCX_FILE])
def test_msoffice_crypto_tools(path: Path):
    # Not so different to msoffcrypto-tool's example:
    # https://github.com/nolze/msoffcrypto-tool#as-library
    encrypted = io.BytesIO(path.read_bytes())
    stream = io.BytesIO()

    office_file = msoffcrypto.OfficeFile(encrypted)

    office_file.load_key(password="not_test")
    with pytest.raises(msoffcrypto.exceptions.InvalidKeyError):
        office_file.decrypt(stream)

    office_file.load_key(password="test")
    office_file.decrypt(stream)
