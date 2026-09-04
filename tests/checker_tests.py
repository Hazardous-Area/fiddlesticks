import stat
import subprocess
from unittest.mock import patch

import pytest

from fiddlesticks import (
    IS_WINDOWS,
    _make_new_tmp_sub_dir,
    check_passwords_sequentially,
    make_py_avdu_aegis_checker,
    make_pykeepass_checker,
    make_ssh_key_checker,
    make_subprocess_checker,
    make_MS_Office_files_key_checker,
)

from .helpers import (
    DOCX_FILE
    KDBX_TEST_VAULT,
    SEVEN_ZIP_TEST_ARCHIVE,
    XLSX_FILE,
    _assert_output_on_found_password,
    _try_make_ssh_key_files,
    avdu_test_vault,  # noqa: F401
)


@pytest.mark.skipif(
    IS_WINDOWS, reason="I haven't figured out the 7zip CLI on Windows yet"
)
def test_is_7zip_installed():
    args = ["7z", "--help"]
    subprocess.run(args, capture_output=True, check=True)


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


def test_make_new_tmp_sub_dir(tmp_path, capsys):
    _make_new_tmp_sub_dir("", tmp_path)
    # repeat to test while loop, and append a suffix.
    _make_new_tmp_sub_dir("", tmp_path)
    capsys.readouterr()


def test_make_subprocess_checker(tmp_path):
    script = tmp_path / "extract_with_7z.sh"
    script.write_text(f"""\
#!/usr/bin/env bash
set -eu

7z x -p$1 -o{tmp_path} {SEVEN_ZIP_TEST_ARCHIVE}
""")
    script.chmod(script.stat().st_mode | stat.S_IXUSR | stat.S_IRUSR)
    checker = make_subprocess_checker(f"{script} ")
    assert checker("test")


def test_sequential_passwords_checker_verbosity_2(capsys):
    result = check_passwords_sequentially(
        candidates=[("A", 0), ("B", 0), ("C", 0)],
        test_func=lambda candidate: False,
        verbosity=2,
        update_every=1,
        total=3,
        print_passwords=True,
    )
    capsys.readouterr()
    assert result is None


def test_ssh_key_checker(tmp_path):
    ssh_test_keys = _try_make_ssh_key_files(tmp_path)
    for key_file, pw in ssh_test_keys:
        assert key_file.is_file()
        checker = make_ssh_key_checker(key_file)
        assert not checker("incorrect")
        assert checker(pw)


@pytest.mark.parametrize(
    "print_passwords",
    [True, False],
)
def test_ssh_key_checker_no_username_finds_password_on_init(
    print_passwords: bool,
    tmp_path,
    capsys,
):
    keyfiles_and_pwds = _try_make_ssh_key_files(tmp_path, "password123")
    with patch("getpass.getuser", side_effect=OSError):
        for file, _pwd in keyfiles_and_pwds:
            with pytest.raises(SystemExit):
                make_ssh_key_checker(file, print_passwords=print_passwords)
            stdout, stderr = capsys.readouterr()
            _assert_output_on_found_password(
                "password123", -12345, print_passwords, stdout, stderr
            )


def test_ssh_key_checker_bad_file(tmp_path):
    file = tmp_path / "test_bad_key"
    file.write_bytes(b"oh2343gsbnwRPJWG32546OMPJDFAFSDGH&53423NZjiga")
    with pytest.raises(ExceptionGroup):
        make_ssh_key_checker(file)

@pytest.mark.parametrize("path", [XLSX_FILE, DOCX_FILE])
def test_ms_office_crypto_tool_checker(path: Path):
    checker = make_MS_Office_files_key_checker(path)
    assert not checker("not_test")
    assert checker("test")


