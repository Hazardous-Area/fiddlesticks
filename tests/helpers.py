
import string
import subprocess
import sys
from pathlib import Path

import pytest
from hypothesis.strategies import (
    binary,
    composite,  # Can be slow
    integers,
    lists,
    sampled_from,
    text,
    tuples,
)

import fiddlesticks

IS_WINDOWS = sys.platform == "win32"
BI_MAP = fiddlesticks.SHIFT_AND_LEET_BI_MAP

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

# We use single quotes to pass the PW guess as a Bash literal string.  
# Otherwise much more complicated escaping rules are required.
password_chars -= {"'"}

passwords = text(
    alphabet="".join(password_chars),
    min_size=1,
    max_size=40,
)


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

@composite
def _alts_and_num_subs_from_password(
    draw,
    password: str,
    max_num_subs: int = 3,
    ):

    all_alts = []
    for i, c in enumerate(password):
        alts = set(BI_MAP.get(c))
        # To allow passing of PW guesses in single quotes via Bash, 
        alts -= {"'"}
        if alts:
            all_alts.append((i, "".join(alts)))

    num_subs = draw(integers(min_value=0, max_value=min(max_num_subs, len(all_alts))))

    selected_alts = draw(
        lists(
            sampled_from(all_alts),
            min_size=num_subs,
            max_size=num_subs,
            unique=True,
        )
    )
    return selected_alts, num_subs

@composite
def selected_alts_and_num_subs_from_password(
    draw,
    password: str,
    max_num_subs: int = 3,
    ):
    selected_alts, num_subs = draw(_alts_and_num_subs_from_password(password, max_num_subs))
    return selected_alts, num_subs

@composite
def guesses_from_alts(
    draw,
    password: str,
    selected_alts: list[tuple[int,str]],
    ):
    
    chars = list(password)
    for i, alts in selected_alts:
        chars[i] = draw(sampled_from(alts))
    return "".join(chars)

@composite
def guesses_and_num_subs_from_password(
    draw,
    password: str,
    max_num_subs: int = 3,
    ):
    selected_alts, num_subs = draw(selected_alts_and_num_subs_from_password(password, max_num_subs))
    guess = draw(guesses_from_alts(password, selected_alts))
    return guess, num_subs

@composite
def passwords_guesses_and_num_subs(
    draw,
    max_num_subs: int = 3,
    ):
    
    password = draw(passwords)
    guess, num_subs = draw(guesses_and_num_subs_from_password(password, max_num_subs))
    return password, guess, num_subs




def _assert_candidate_within_M_of_pwd(candidate: str, pwd: str, M: int) -> None:
    # Current implementation preserves length
    assert len(pwd) == len(candidate)
    i = 0
    for c1, c2 in zip(pwd, candidate):
        if c1 != c2:
            i += 1
            assert c2 in BI_MAP[c1], f"Unrelated: {c1}, {c2}"
    assert i <= M


@pytest.fixture(scope="session")
def avdu_test_vault(tmp_path):
    subprocess.run(
        f"git clone --depth=1 https://github.com/Sammy-T/avdu/ {tmp_path}",
        check=True,
        capture_output=True,
    )
    return tmp_path / "main" / "test" / "aegis_encrypted.json"
    
