from pathlib import Path
import random
import shutil
import string
import subprocess
import sys
import tempfile

import pytest
from hypothesis import given, settings, HealthCheck, Phase
from hypothesis.strategies import (
    lists,
    tuples,
    text,
    characters,
    binary,
)

import fiddlesticks

IS_WINDOWS = sys.platform=="win32"

@pytest.mark.skipif(IS_WINDOWS, reason="I haven't figured out the 7zip CLI on Windows yet")
def test_is_7zip_installed():
    args = ["7z", "--help"]
    result = subprocess.run(args, capture_output=True)
    assert result.returncode == 0

file_names = text(
    alphabet=string.ascii_letters + string.digits,
    # characters(
    #     codec="ascii",
    #     exclude_categories=["Cs", "Co", "Cn"],
    # ),
    min_size=1,
    max_size=24,
)
file_names_and_contents = lists(
    tuples(file_names, binary(min_size=1, max_size=1024)),
    min_size=1,
    max_size=20,
    unique_by=lambda x: x[0],
)

password_chars = set(string.ascii_letters + string.digits + string.punctuation)
#To void password chars being parsed as control chars by Bash
# password_chars -= set("\\"+r"'&;*:{$") 

passwords = text(
    alphabet="".join(password_chars),
    min_size=1,
    max_size=40,
)

BI_MAP = fiddlesticks.SHIFT_AND_LEET_BI_MAP

# Don't include ' being interpreted as a Bash control char
# in the tests
del BI_MAP["'"]
for k in list(BI_MAP):
    if "'" in BI_MAP[k]:
        del BI_MAP[k]

def _get_num_subs(pwd: str) -> int:
    L = len(pwd)
    return min(L, 4)

@pytest.mark.hypothesis
@pytest.mark.slow
@given(pwd=passwords)
@settings(deadline=None, suppress_health_check=[HealthCheck.too_slow, HealthCheck.data_too_large])
def test_alt_chars_candidates_generator(pwd: str):
    M = _get_num_subs(pwd)
    total, candidates = fiddlesticks.candidate_passwords_from_alt_chars(pwd, M)
    for candidate in candidates:
        # Current implementation preserves length
        assert len(pwd) == len(candidate)
        i = 0
        for c1, c2 in zip(pwd, candidate):
            if c1 != c2:
                i += 1
                assert c1 in BI_MAP[c2] or c2 in BI_MAP[c1], f"Unrelated: {c1}, {c2}"
        assert i <= M

def _create_password_protected_7z_archive(
    dir_: Path,
    file_names_and_contents: list[tuple[str, bytes]],
    password: str,
):
    dir_.mkdir(exist_ok=True, parents=True)
    for file_name, content in file_names_and_contents:
        (dir_ / file_name).write_bytes(content)

def _assert_files_same(
    dir_: Path,
    file_names_and_contents: list[tuple[str, bytes]],
):
    for file_name, content in file_names_and_contents:
        actual = (dir_ / file_name).read_bytes()
        assert actual == content, f"File did not round trip.  Expected: {content=}.  Got: {actual=}"

def _guess_from_password(
    password: str,
    max_subs: int,
) -> str:
    indices_and_alt_chars_with_alts = []
    for i, c in enumerate(password):
        alts = BI_MAP.get(c)
        if alts:
            indices_and_alt_chars_with_alts.append((i, alts))

    chars = list(password)
    max_subs = min(max_subs, len(indices_and_alt_chars_with_alts))

    for i, alts in random.sample(indices_and_alt_chars_with_alts, max_subs):
        chars[i] = random.choice(alts)
    return "".join(chars)

@pytest.mark.hypothesis
@pytest.mark.slow
@pytest.mark.skipif(IS_WINDOWS, reason="I haven't figured out the 7zip CLI on Windows yet")
@settings(
    max_examples=50,
    phases=[Phase.explicit, Phase.reuse, Phase.generate],  # Skip shrinking
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.data_too_large],
    deadline=None,
)
@given(
    file_names_and_contents=file_names_and_contents,
    password=passwords,
)
def test_7zip_checker(
    file_names_and_contents: list[tuple[str, bytes]],
    password: str,
):  
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
        )
        assert result.returncode == 0, f"Could not create 7z archive from: {password=}, containing: {file_names_and_contents}"

        test_extracted_dir = tmp_path / "test_extracted"
        test_extracted_dir.mkdir()

        result = subprocess.run(
            ["7z", "x", f"-p{password}", f"-o{test_extracted_dir}", archive],
            capture_output=True,
        )
        assert result.returncode == 0, f"Could not extract {archive} with known good: {password=}, with 7z directly"

        _assert_files_same(test_extracted_dir / "contents", file_names_and_contents)

        shutil.rmtree(test_extracted_dir)
        test_extracted_dir.mkdir()

        max_subs = _get_num_subs(password)
        guess = _guess_from_password(password, max_subs)


        result = subprocess.run(
            ["fiddlesticks","--7zip", 
             "--max-subs", f"{max_subs}",
             f"--extract-to={test_extracted_dir}", 
             f"--password-guess={guess}", archive
            ],
            capture_output=True,
        )
        assert result.returncode==0, f"Could not crack: {password} from: {guess=} for {archive}, {max_subs=}"

        _assert_files_same(test_extracted_dir / "contents", file_names_and_contents)






