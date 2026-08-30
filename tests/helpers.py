
import string
import sys
from pathlib import Path

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
def passwords_alts_and_num_subs(
    draw,
    max_num_subs: int = 3,
    ):
    password = draw(passwords)

    indices_and_alts = []
    for i, c in enumerate(password):
        alts = set(BI_MAP.get(c))
        # To passing of PW guesses in single quotes via Bash, 
        alts -= {"'"}
        if alts:
            indices_and_alts.append((i, "".join(alts)))

    num_subs = draw(integers(min_value=0, max_value=min(max_num_subs, len(indices_and_alts))))

    all_alts = draw(
        lists(
            sampled_from(indices_and_alts),
            min_size=num_subs,
            max_size=num_subs,
            unique=True,
        )
    )
    return password, all_alts, num_subs

@composite
def passwords_guesses_and_num_subs(
    draw,
    max_num_subs: int = 3,
    ):
    
    password, all_alts, num_subs = draw(passwords_alts_and_num_subs(max_num_subs))

    chars = list(password)

    for i, alts in all_alts:
        chars[i] = draw(sampled_from(alts))

    return password, "".join(chars), num_subs



def _assert_candidate_within_M_of_pwd(candidate: str, pwd: str, M: int) -> None:
    # Current implementation preserves length
    assert len(pwd) == len(candidate)
    i = 0
    for c1, c2 in zip(pwd, candidate):
        if c1 != c2:
            i += 1
            assert c2 in BI_MAP[c1], f"Unrelated: {c1}, {c2}"
    assert i <= M