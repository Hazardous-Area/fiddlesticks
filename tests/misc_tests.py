import builtins  # noqa: F401
import contextlib
import io
import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import msoffcrypto
import msoffcrypto.exceptions
import pytest
from cryptography.hazmat.primitives.serialization import (
    load_pem_private_key,
    load_ssh_private_key,
)
from hypothesis import HealthCheck, given, settings
from hypothesis.strategies import composite, integers, lists

from fiddlesticks import (
    IS_WINDOWS,
    _get_hopefully_incorrect_password,
    cli,
    handle_found_password,
    offer_to_skip_indices_ruled_out_by_progress_file,
    save_ruled_out_indices_to_progress_file,
)

from .helpers import (
    DOCX_FILE,
    SEVEN_ZIP_TEST_ARCHIVE,
    XLSX_FILE,
    _assert_output_on_found_password,
    _create_random_progress_file,
    _try_make_ssh_key_files,
)


@pytest.mark.skipif(
    IS_WINDOWS, reason="I haven't figured out the 7zip CLI on Windows yet"
)
def test_password_from_getpass_in_CLI(capsys):
    with patch("getpass.getpass", side_effect=["test", ""]):
        assert 0 == cli(
            ["--new-search", "--max-subs", "0", str(SEVEN_ZIP_TEST_ARCHIVE)]
        )
    capsys.readouterr()


def test_get_hopefully_incorrect_password_username_not_found(capsys):
    with patch("getpass.getuser", side_effect=OSError):
        assert "password123" == _get_hopefully_incorrect_password()


@pytest.mark.parametrize(
    "print_passwords",
    [True, False],
)
def test_handle_found_password_no_time(
    print_passwords: bool,
    capsys,
):
    password = "abcde"
    i = 5
    # This currently only gets called without a calculation time
    # if the password was the user's username, or "password123",
    # when using an SSH key password checker.
    handle_found_password(
        password=password,
        i=i,
        t=None,
        print_passwords=print_passwords,
    )

    stdout, stderr = capsys.readouterr()
    _assert_output_on_found_password(password, i, print_passwords, stdout, stderr)


@pytest.mark.skipif(
    IS_WINDOWS, reason="I haven't figured out the OpenSSH CLI on Windows yet"
)
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


def test_offer_to_skip_indices_ruled_out_by_progress_file(tmp_path, capsys):
    progress_file, indices = _create_random_progress_file(
        tmp_path / "test_progress_file.json"
    )

    with patch("builtins.input", side_effect=["y"]):
        assert indices[0] + 1 == offer_to_skip_indices_ruled_out_by_progress_file(
            force_resume=False,
            saved_progress_file=progress_file,
        )
    capsys.readouterr()


def test_bad_progress_file(tmp_path):
    progress_file = tmp_path / "test_progress_file.json"
    progress_file.write_text("{")  # Invalid JSON

    index = offer_to_skip_indices_ruled_out_by_progress_file(
        force_resume=False,
        saved_progress_file=progress_file,
    )
    assert index == 0


def test_user_declines_to_skip_indices_ruled_out_by_progress_file(tmp_path, capsys):
    progress_file, _ = _create_random_progress_file(
        tmp_path / "test_progress_file.json"
    )

    with patch("builtins.input", side_effect=["n"]):
        index = offer_to_skip_indices_ruled_out_by_progress_file(
            force_resume=False,
            saved_progress_file=progress_file,
        )
    assert index == 0
    capsys.readouterr()


@composite
def ruled_out_candidates_indices(draw) -> tuple[list[int], int]:
    i = draw(integers(min_value=0))
    j = draw(integers(min_value=i, max_value=i + 1000))
    extras = draw(lists(integers(min_value=j + 2, max_value=j + 1000), max_size=100))
    return [*range(i, j + 1), *extras], j


@pytest.mark.skipif(IS_WINDOWS, reason="Crashes_with_memory_error")
@pytest.mark.hypothesis
@pytest.mark.slow
@settings(
    max_examples=3,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.data_too_large],
    deadline=None,
    database=None,
    derandomize=True,  # Without this, the test doesn't complete in less than 5 mins in Github Actions
    # (despite that the default is True in CI ???
    # https://hypothesis.readthedocs.io/en/latest/reference/api.html#hypothesis.settings.derandomize )
)
@given(args=ruled_out_candidates_indices())
def test_save_ruled_out_indices_to_progress_file(args: tuple[list[int], int]):
    untrimmed_indices, smallest_after_trimming = args

    stream = io.StringIO()
    # Just create a tempdir manually as hypothesis' decorators
    # don't play nicely with test functions
    # that use function-scoped fixtures like Pytest's tmp_path.
    with contextlib.redirect_stderr(stream), tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        progress_file = tmp_path / "test_progress_file.json"
        save_ruled_out_indices_to_progress_file(untrimmed_indices, progress_file)
        trimmed_indices = json.loads(progress_file.read_text())[
            "ruled_out_candidates_indices"
        ]

        starting_index = offer_to_skip_indices_ruled_out_by_progress_file(
            True, progress_file
        )

    assert smallest_after_trimming == trimmed_indices[0]
    assert smallest_after_trimming + 1 == starting_index
