import string
import subprocess
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

BI_MAP = fiddlesticks.SHIFT_AND_LEET_BI_MAP
PARENT_DIR = Path(__file__).parent
DATA_FILES = PARENT_DIR / "data_files"
KDBX_TEST_VAULT = DATA_FILES / "Test_vault_Do_Not_Use.kdbx"
SEVEN_ZIP_TEST_ARCHIVE = DATA_FILES / "foo.7z"
XLSX_FILE = DATA_FILES / "test.xlsx"
DOCX_FILE = DATA_FILES / "test.docx"

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

base_password_chars = set(string.ascii_letters + string.digits + string.punctuation)
BASH_CONTROL_CHARS = set("'&:$;|<>()\\ \".*{}?[]#!~-=")
# We use single quotes to pass the PW guess as a Bash literal string.
# Otherwise much more complicated escaping rules are required.
chars_without_Bash_syntax = base_password_chars - BASH_CONTROL_CHARS


def passwords(
    password_chars: set[str] = base_password_chars,
):
    return text(
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
        assert actual == content, (
            f"File did not round trip.  Expected: {content=}.  Got: {actual=}"
        )


@composite
def _alts_and_num_subs_from_password(
    draw,
    password: str,
    max_num_subs: int = 3,
    password_chars: set[str] = base_password_chars,
):

    all_alts = []
    for i, c in enumerate(password):
        alts = {alt for alt in BI_MAP.get(c, []) if alt in password_chars}
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
def guesses_from_alts(
    draw,
    password: str,
    selected_alts: list[tuple[int, str]],
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
    password_chars: set[str] = base_password_chars,
):
    selected_alts, num_subs = draw(
        _alts_and_num_subs_from_password(password, max_num_subs, password_chars)
    )
    guess = draw(guesses_from_alts(password, selected_alts))
    return guess, num_subs


@composite
def passwords_guesses_and_num_subs(
    draw,
    max_num_subs: int = 3,
    password_chars: set[str] = base_password_chars,
):

    password = draw(passwords(password_chars))
    guess, num_subs = draw(
        guesses_and_num_subs_from_password(password, max_num_subs, password_chars)
    )
    return password, guess, num_subs


def _candidate_is_within_M_of_pwd(
    candidate: str,
    pwd: str,
    M: int,
    mapping: dict[str, list[str]] = BI_MAP,
) -> bool:
    # Current implementation preserves length
    if len(pwd) != len(candidate):
        return False

    num_subs = 0
    for c1, c2 in zip(pwd, candidate):
        if c1 != c2:
            num_subs += 1
            if c2 not in mapping[c1]:
                return False

    return num_subs <= M


def _assert_candidate_within_M_of_pwds(
    candidate: str,
    pwds: list[str],
    M: int,
    mapping: dict[str, list[str]] = BI_MAP,
) -> None:
    assert any(
        _candidate_is_within_M_of_pwd(candidate, pwd, M, mapping) for pwd in pwds
    )


@pytest.fixture(scope="session")
def avdu_test_vault(tmp_path_factory):
    avdu_repo = tmp_path_factory.mktemp("avdu")
    subprocess.run(
        [
            "git",
            "clone",
            "--depth=1",
            "https://github.com/Sammy-T/avdu/",
            str(avdu_repo),
        ],
        check=True,
        capture_output=True,
    )
    return avdu_repo / "test" / "data" / "aegis_encrypted.json"


def _try_make_ssh_key_files(
    keys_dir: Path, password: str = ""
) -> list[tuple[Path, str]]:
    keyfiles_and_pwds = []
    for cmd, pwd, key_file in [
        (
            'openssl genrsa -aes128 -passout pass:{password} -out "{key_file}" 2048',
            "test",
            "openssl_PEM.key",
        ),
        (
            'ssh-keygen -m PEM -t rsa -b 2048 -N "{password}" -f "{key_file}"',
            "testtest",
            "basic_PEM.key",
        ),
        (
            'ssh-keygen -t rsa -b 2048 -N "{password}" -f "{key_file}"',
            "testtest",
            "openssh-modern.key",
        ),
    ]:
        pwd = password or pwd
        subprocess.run(
            cmd.format(password=pwd, key_file=(keys_dir / key_file).as_posix()),
            check=True,
            capture_output=True,
            shell=True,
        )
        keyfiles_and_pwds.append((keys_dir / key_file, pwd))
    return keyfiles_and_pwds


def _assert_output_on_found_password(
    password: str,
    i: int,
    print_passwords: bool,
    stdout: str,
    stderr: str,
) -> None:
    assert not stdout
    assert "Found password" in stderr, f"{stderr=}"
    assert f"candidate number: {i}" in stderr, f"{stderr=}"
    if print_passwords:
        assert password in stderr, f"{stderr=}"
    else:
        assert password not in stderr, f"{stderr=}"
