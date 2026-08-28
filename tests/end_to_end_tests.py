import shutil
import subprocess
import tempfile
from collections.abc import Callable
from pathlib import Path

import pytest
from hypothesis import HealthCheck, Phase, given, settings
from hypothesis.strategies import integers

import fiddlesticks

from .helpers import (
    IS_WINDOWS,
    _assert_candidate_within_M_of_pwd,
    _assert_files_same,
    _create_password_protected_7z_archive,
    _get_num_subs,
    _guess_from_password,
    file_names_and_contents,
    passwords,
)

# A module scoped fixture is ideal for this.  But that 
# needs mocks, patches or plug-ins etc.
# Just make a copy including the required changes
# and shadow the target. 
BI_MAP_WITHOUT_SINGLE_QUOTES = {
    k: v for k, v in fiddlesticks.SHIFT_AND_LEET_BI_MAP.items()
    # Don't include "'" in the tests, 
    # as it may be interpreted on the command line 
    # as a Bash control character (literal str delimiter)
    if k != "'"
    if "'" not in v
}
BI_MAP = BI_MAP_WITHOUT_SINGLE_QUOTES

def _collate_args(num_subs: int, guess: str, *args: str) -> list[str]:
    return [
        "fiddlesticks",
        "--max-subs", f"{num_subs}",
        f"--password-guess={guess}",
        *args
    ]

def make_internal_checker_args_collater(
    checker: str,
    ) -> Callable[[int, Path, str, str], list[str]]:
    def collater(num_subs: int, test_extracted_dir: Path, guess: str, archive: str):
        return _collate_args(
            num_subs,
            guess,
            checker, 
            f"--extract-to={test_extracted_dir}", 
            archive,
        )
    return collater

def shell_collater(num_subs: int, test_extracted_dir: Path, guess: str, archive: str):
        return _collate_args(
            num_subs,
            guess,
            "--shell", 
            "--", # Tell argparse all subsequent args are positional
            "7z", # Taken from make_7zip_checker
            "x",
            f"-o{test_extracted_dir}",
            archive,
            "-p",
        )

@pytest.mark.hypothesis
@pytest.mark.slow
@pytest.mark.skipif(IS_WINDOWS, reason="I haven't figured out the 7zip CLI on Windows yet")
@settings(
    max_examples=10,
    phases=[Phase.explicit, Phase.reuse, Phase.generate],  # Skip shrinking
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.data_too_large],
    deadline=None,
    derandomize=True, # Without this, the test doesn't complete in less than 5 mins in Github Actions 
    # (despite that the default is True in CI ???
    # https://hypothesis.readthedocs.io/en/latest/reference/api.html#hypothesis.settings.derandomize )
)
@pytest.mark.parametrize("make_args",[
    make_internal_checker_args_collater("--7zip"),
    make_internal_checker_args_collater("--7zip-persistent"),
    make_internal_checker_args_collater("--py7zr"),
    shell_collater,
])
@given(
    file_names_and_contents=file_names_and_contents,
    password=passwords,
)
def test_7z_archives_extracted_via_fiddlesticks_CLI(
    file_names_and_contents: list[tuple[str, bytes]],
    password: str,
    make_args: Callable[[int, Path, str,str], list[str]],
):  

    MAX_NUM_SUBS: int = 3


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
        assert result.returncode == 0, f"Could not create 7z archive from: {password=}, containing: {file_names_and_contents}"

        test_extracted_dir = tmp_path / "test_extracted"
        test_extracted_dir.mkdir()

        # Test if extraction directly with 7z actually works in the test env,
        # before testing if fiddlesticks can do this too.
        result = subprocess.run(
            ["7z", "x", f"-p{password}", f"-o{test_extracted_dir}", archive],
            capture_output=True,
            check=False,
        )
        assert result.returncode == 0, f"Could not extract {archive} with known good: {password=}, with 7z directly"

        _assert_files_same(test_extracted_dir / "contents", file_names_and_contents)

        shutil.rmtree(test_extracted_dir)
        test_extracted_dir.mkdir()

        num_subs = _get_num_subs(password, MAX_NUM_SUBS)
        guess = _guess_from_password(password, num_subs)


        result = subprocess.run(
            make_args(num_subs, test_extracted_dir, guess, archive),
            capture_output=True,
            check=False,
        )
        assert result.returncode==0, f"Could not crack: {password} from: {guess=} for {archive}, {num_subs=}"

        _assert_files_same(test_extracted_dir / "contents", file_names_and_contents)



@pytest.mark.hypothesis
@pytest.mark.slow
@pytest.mark.skipif(IS_WINDOWS, reason="I haven't figured out the 7zip CLI on Windows yet")
@settings(
    max_examples=10,
    phases=[Phase.explicit, Phase.reuse, Phase.generate],  # Skip shrinking
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.data_too_large],
    deadline=None,
    derandomize=True, # Without this, the test doesn't complete in less than 5 mins in Github Actions 
    # (despite that the default is True in CI ???
    # https://hypothesis.readthedocs.io/en/latest/reference/api.html#hypothesis.settings.derandomize )
)
@given(
    password=passwords,
    num_subs=integers(min_value=0, max_value=5),
)
def test_piping_candidates_to_stdout(
    password: str,
    num_subs: int,
):  

    guess = _guess_from_password(password, num_subs)


    result = subprocess.run(
        _collate_args(num_subs, guess, "--pipe"),
        capture_output=True,
        check=False,
    )
    assert result.returncode==0, f"Could not --pipe candidate passwords, {num_subs=}, {guess=}"

    for candidate in result.stdout.decode().splitlines():
        _assert_candidate_within_M_of_pwd(candidate, password, M=num_subs)



