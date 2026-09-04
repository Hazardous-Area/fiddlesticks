import json
import os
import shlex
import shutil
import stat
import subprocess
import tempfile
from collections.abc import Callable
from pathlib import Path

import pytest
from hypothesis import HealthCheck, Phase, given, settings

import fiddlesticks
from fiddlesticks import IS_WINDOWS

from .helpers import (
    BI_MAP,
    KDBX_TEST_VAULT,
    SEVEN_ZIP_TEST_ARCHIVE,
    _assert_candidate_within_M_of_pwds,
    _assert_files_same,
    _create_password_protected_7z_archive,
    _try_get_avdu_vault,
    chars_without_Bash_syntax,
    file_names_and_contents,
    guesses_and_num_subs_from_password,
    passwords_guesses_and_num_subs,
)


def test_CLI_with_no_args():
    result = subprocess.run(["fiddlesticks"], capture_output=True, check=False)

    assert result.returncode == 0

    # Test splitlines to avoid failing on Windows due to line endings.
    output = result.stderr.decode().splitlines()
    expected = fiddlesticks.parser.format_help().splitlines()
    assert output == expected


def test_print_alt_char_map_is_valid_JSON():
    result = subprocess.run(
        ["fiddlesticks", "--print-char-map", "--shift_and_leet"],
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, "Error when printing alt char map"
    assert json.loads(result.stderr.decode()) == BI_MAP


@pytest.mark.parametrize(
    "guesses,num_subs,mapping,expected,verbosity",
    [
        (
            ["ABC"],
            2,
            {
                "A": ["Y"],
                "B": ["Z"],
            },
            {"ABC", "AZC", "YBC", "YZC"},
            0,
        ),
        (
            ["AB", "DE"],
            2,
            {
                "A": ["Y"],
                "B": ["X"],
                "D": ["Z"],
            },
            {"AB", "AX", "DE", "YB", "ZE", "YX"},
            0,
        ),
    ]
    + [(["A"] * 3000, 0, {}, {"A"}, i) for i in range(4)],
)
def test_piping_candidates_from_alt_char_map(
    guesses: list[str],
    num_subs: int,
    mapping: dict[str, list[str]],
    tmp_path,
    expected: set[str],
    verbosity: int,
):
    mapping_file = tmp_path / "test.json"
    mapping_file.write_text(json.dumps(mapping))
    optional_args = [f"--char-map={mapping_file}"]

    if verbosity:
        optional_args.append(f"-{'v' * verbosity}")
    result = subprocess.run(
        _collate_args(num_subs, guesses, "--pipe", *optional_args),
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, (
        f"Could not --pipe candidate passwords, {num_subs=}, {guesses=}, {mapping_file=}"
    )

    candidates = set()
    for candidate in result.stdout.decode().splitlines():
        _assert_candidate_within_M_of_pwds(
            candidate, guesses, M=num_subs, mapping=mapping
        )
        candidates.add(candidate)

    assert candidates == expected, (
        f"Missing, or unexpected candidates in {candidates}.  Expected: {expected}"
    )

    if verbosity:
        assert len(result.stderr) > 0


def _run_fiddlesticks_without_extract_to(
    max_num_subs: int,
    guesses: list[str],
    file: Path | None,
    _tmp_dir_path: str | Path,
    *args: str,
):
    other_args = list(args)
    if file is not None:
        other_args.append(str(file))

    return subprocess.run(
        _collate_args(max_num_subs, guesses, *other_args),
        capture_output=True,
        check=False,
        env={
            "TMPDIR": str(_tmp_dir_path),
            **os.environ,
        },  # Within the subprocess, tempfile.gettmpdir searches $TMPDIR
    )


@pytest.mark.parametrize(
    "file",
    [
        # The passwords for all the files below, should all be "test"
        KDBX_TEST_VAULT,
        SEVEN_ZIP_TEST_ARCHIVE,
    ],
)
def test_default_command_from_file_ext(file, tmp_path):
    result = _run_fiddlesticks_without_extract_to(2, ["7est"], file, tmp_path)
    assert result.returncode == 0


@pytest.mark.parametrize(
    "command",
    [
        "--py7zr",
        "--7zip-persistent",
    ],
)
def test_other_7z_checkers_without_extract_to(command, tmp_path):
    result = _run_fiddlesticks_without_extract_to(
        2, ["7est"], SEVEN_ZIP_TEST_ARCHIVE, tmp_path, command
    )
    assert result.returncode == 0


def test_default_command_with_aegis_vault(tmp_path):
    avdu_test_vault = _try_get_avdu_vault(tmp_path)
    result = subprocess.run(
        _collate_args(2, ["7est"], avdu_test_vault),
        capture_output=True,
        check=False,
        env={"TMPDIR": str(tmp_path), **os.environ},
    )
    assert result.returncode == 0


def test_update_every(tmp_path):
    result = _run_fiddlesticks_without_extract_to(
        2,
        ["7est"],
        None,
        tmp_path,
        "--pipe",
        "--update-every=10",
    )
    assert result.returncode == 0


def test_input_and_output_file(tmp_path):
    guesses = ["test"]
    guesses_file = tmp_path / "guesses.txt"
    guesses_file.write_text("\n".join(guesses))
    output_file = tmp_path / "output.txt"

    result = subprocess.run(
        [
            "fiddlesticks",
            "--max-subs=0",
            "--py7zr",
            f"--input-file={guesses_file}",
            f"--output-file={output_file}",
            str(Path(__file__).parent / "foo.7z"),
        ],
        capture_output=True,
        check=True,
        env={
            "TMPDIR": str(tmp_path),
            **os.environ,
        },  # Within the subprocess, tempfile.gettmpdir searches $TMPDIR
    )
    assert result.returncode == 0
    assert output_file.read_text() == guesses[0]


def test_update_every_verbosity_2_and_print_password(tmp_path):
    result = _run_fiddlesticks_without_extract_to(
        0,
        ["A"] * 6,
        None,
        tmp_path,
        "--pipe",
        "-vv",
        "--update-every=2",
        "--print-passwords",
    )
    assert result.returncode == 0


def test_default_with_a_shell_command(tmp_path):
    guesses = ["A"]
    result = _run_fiddlesticks_without_extract_to(0, guesses, None, tmp_path, "echo ")
    assert result.returncode == 0


def test_default_with_a_shell_script_file(tmp_path):
    # Try to trigger the shell=False flavour of subprocess checker
    script = tmp_path / "extract_with_7z.sh"
    script.write_text(f"""\
#!/usr/bin/env bash
set -eu

7z x -p$1 -o{tmp_path} {SEVEN_ZIP_TEST_ARCHIVE}
""")
    script.chmod(script.stat().st_mode | stat.S_IXUSR | stat.S_IRUSR)
    guesses = ["test"]
    result = _run_fiddlesticks_without_extract_to(
        0,
        guesses,
        None,
        tmp_path,
        f"{script} ",  # Ends in space.  Appended PW becomes $1
    )
    assert result.returncode == 0


def test_default_without_a_file_or_shell_command(tmp_path):
    result = _run_fiddlesticks_without_extract_to(
        0,
        ["A"],
        None,
        tmp_path,
    )
    assert result.returncode != 0  # Should raise the ValueError for missing *args


def _collate_args(
    num_subs: int,
    guesses: list[str],
    *args: str,
    shell: bool = False,
) -> list[str]:
    # Collates args for subprocess.run, the entire command
    # used to test fiddlesticks.  I.e. not necessarily just
    # the args for fiddlesticks, e.g. Bash external to it
    # could be included too.
    pwd_args = [f"--password-guess={guess}" for guess in guesses]
    if shell:
        pwd_args = [shlex.quote(pwd_arg) for pwd_arg in pwd_args]
    return [
        "fiddlesticks",
        "--max-subs",
        f"{num_subs}",
        *pwd_args,
        *args,
    ]


def make_internal_checker_args_collater(
    checker: str,
) -> Callable[[int, Path, str, str], list[str]]:
    def collater(num_subs: int, test_extracted_dir: Path, guess: str, file: str):
        return _collate_args(
            num_subs,
            [guess],
            checker,
            f"--extract-to={test_extracted_dir}",
            file,
        )

    return collater


def shell_collater(num_subs: int, test_extracted_dir: Path, guess: str, file: str):
    return _collate_args(
        num_subs,
        [guess],
        "--shell",
        "--",  # Tell argparse all subsequent args are positional
        "7z",  # Taken from make_7zip_checker
        "x",
        f"-o{test_extracted_dir}",
        file,
        "-p",
    )


def pipe_to_bash_while_loop_collater(
    num_subs: int, test_extracted_dir: Path, guess: str, file: str
):

    script_text = fiddlesticks.PERSISTENT_7Z_CHECKER_OUTLINE.format(
        extract_to=str(test_extracted_dir),
        file=file,
    )
    script = Path("persistent_checker.sh")
    script.write_text(script_text)
    script.chmod(script.stat().st_mode | stat.S_IXUSR | stat.S_IRUSR)

    return _collate_args(
        num_subs,
        [guess],
        "--pipe",
        "--",
        "|",
        str(script.resolve()),
        shell=True,
    )


@pytest.mark.hypothesis
@pytest.mark.slow
@pytest.mark.skipif(
    IS_WINDOWS, reason="I haven't figured out the 7zip CLI on Windows yet"
)
@settings(
    max_examples=3,
    phases=[Phase.explicit, Phase.reuse, Phase.generate],  # Skip shrinking
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.data_too_large],
    deadline=None,
    # derandomize=True, # Without this, the test doesn't complete in less than 5 mins in Github Actions
    # # (despite that the default is True in CI ???
    # # https://hypothesis.readthedocs.io/en/latest/reference/api.html#hypothesis.settings.derandomize )
)
@given(
    password_guess_and_num_subs=passwords_guesses_and_num_subs(
        max_num_subs=3,
        password_chars=chars_without_Bash_syntax,
    ),
)
def test_piping_candidates_to_stdout(
    password_guess_and_num_subs: tuple[str, str, int],
):

    password, guess, num_subs = password_guess_and_num_subs

    result = subprocess.run(
        _collate_args(num_subs, [guess], "--pipe"),
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, (
        f"Could not --pipe candidate passwords, {num_subs=}, {guess=}"
    )

    candidates = set()
    for candidate in result.stdout.decode().splitlines():
        _assert_candidate_within_M_of_pwds(candidate, [guess], M=num_subs)
        candidates.add(candidate)

    assert password in candidates, (
        f"Did not find {password=} from {guess=}, {num_subs=}, {candidates=}"
    )


# """
# # Run using the encrypted test file. (Enter password "test" when prompted.)
# go run ./cmd/avdu -p test/data/aegis_encrypted.json -e
# https://github.com/Sammy-T/avdu/blob/master/README.md
# """
@pytest.mark.hypothesis
@pytest.mark.slow
@given(guess_and_num_subs=guesses_and_num_subs_from_password("test", max_num_subs=4))
@settings(
    max_examples=3,
    phases=[Phase.explicit, Phase.reuse, Phase.generate],  # Skip shrinking
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.data_too_large],
    deadline=None,
    # derandomize=True, # Without this, the test doesn't complete in less than 5 mins in Github Actions
    # # (despite that the default is True in CI ???
    # # https://hypothesis.readthedocs.io/en/latest/reference/api.html#hypothesis.settings.derandomize )
)
def test_aegis_checker_from_CLI(guess_and_num_subs, tmp_path):
    avdu_test_vault = _try_get_avdu_vault(tmp_path)
    guess, num_subs = guess_and_num_subs
    result = subprocess.run(
        _collate_args(num_subs, [guess], "--aegis", str(avdu_test_vault)),
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, (
        f"Using Aegis encrypted vault checker, could not find 'test' from {guess=}, {num_subs=}"
    )


def test_aegis_checker_errors_from_CLI(tmp_path):
    avdu_test_vault = _try_get_avdu_vault(tmp_path)
    num_subs = 3
    guess = "abcd"  # i.e. not "test" (but not too long either)
    result = subprocess.run(
        _collate_args(
            num_subs,
            [guess],
            "--aegis",
            str(avdu_test_vault),
        ),
        capture_output=True,
        check=False,
    )
    assert result.returncode != 0, (
        f"Failed to error on bad {guess=}, or unexpectedly found password ('test') of Aegis encrypted vault checker, {num_subs=}"
    )


@pytest.mark.hypothesis
@pytest.mark.slow
@pytest.mark.skipif(
    IS_WINDOWS, reason="I haven't figured out the 7zip CLI on Windows yet"
)
@settings(
    max_examples=3,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.data_too_large],
    deadline=None,
    database=None,
    derandomize=True,  # Without this, the test doesn't complete in less than 5 mins in Github Actions
    # (despite that the default is True in CI ???
    # https://hypothesis.readthedocs.io/en/latest/reference/api.html#hypothesis.settings.derandomize )
)
@pytest.mark.parametrize(
    "make_args,shell",
    [
        (make_internal_checker_args_collater("--7zip"), False),
        (make_internal_checker_args_collater("--7zip-persistent"), False),
        (make_internal_checker_args_collater("--py7zr"), False),
        (shell_collater, False),
        (pipe_to_bash_while_loop_collater, True),  # Needs to run a Bash session
    ],
)
@given(
    file_names_and_contents=file_names_and_contents,
    password_guess_and_num_subs=passwords_guesses_and_num_subs(
        max_num_subs=3,
        password_chars=chars_without_Bash_syntax,
    ),
)
def test_7z_archives_extracted_via_fiddlesticks_CLI(
    file_names_and_contents: list[tuple[str, bytes]],
    password_guess_and_num_subs: tuple[str, str, int],
    make_args: Callable[[int, Path, str, str], list[str]],
    shell: bool,
):

    password, guess, num_subs = password_guess_and_num_subs

    # Just create a tempdir manually as hypothesis' decorators
    # don't play nicely with test functions
    # that use function-scoped fixtures like Pytest's tmp_path.
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)

        archive_dir = tmp_path / "contents"

        _create_password_protected_7z_archive(
            archive_dir,
            file_names_and_contents,
            password,
        )

        archive = str(tmp_path / "archive.7z")

        result = subprocess.run(
            ["7z", "a", "-mhe=on", f"-p{password}", archive, str(archive_dir)],
            capture_output=True,
            check=False,
        )
        assert result.returncode == 0, (
            f"Could not create 7z archive from: {password=}, containing: {file_names_and_contents}"
        )

        test_extracted_dir = tmp_path / "test_extracted"
        test_extracted_dir.mkdir()

        # Test if extraction directly with 7z actually works in the test env,
        # before testing if fiddlesticks can do this too.
        result = subprocess.run(
            ["7z", "x", f"-p{password}", f"-o{test_extracted_dir}", archive],
            capture_output=True,
            check=False,
        )
        assert result.returncode == 0, (
            f"Could not extract {archive} with known good: {password=}, with 7z directly"
        )

        _assert_files_same(test_extracted_dir / "contents", file_names_and_contents)

        shutil.rmtree(test_extracted_dir)
        test_extracted_dir.mkdir()

        cmd_args: str | list[str]
        cmd_args = make_args(num_subs, test_extracted_dir, guess, archive)
        if shell:
            cmd_args = " ".join(cmd_args)
        result = subprocess.run(
            cmd_args,
            capture_output=True,
            check=False,
            shell=shell,
        )
        assert result.returncode == 0, (
            f"Could not crack: {password} from: {guess=} for {archive}, {num_subs=}"
        )

        _assert_files_same(test_extracted_dir / "contents", file_names_and_contents)
