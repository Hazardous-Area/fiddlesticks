# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///

# # Non-compliant with PEP 723:
# optional_dependencies = [
#   # External 7zip, e.g.:
#   #   sudo apt-get install -y 7zip
#   ssh = ["bcrypt", "cryptography>=47"], # v47 min for "incorrect PW" error message from Rust code
#   aegis = ["py-avdu"],
#   keepassxc = ["pykeepass"],
#   # External Veracrypt, e.g.:
#   #   sudo add-apt-repository ppa:unit193/encryption
#   #   sudo apt update
#   #   sudo apt install veracrypt
#   msoffice = ["msoffcrypto-tool"]
#   py7zr = ["py7zr"],
# ]
# ///

__version__ = "0.5.0.dev"

import argparse
import atexit
import getpass
import io
import json
import math
import os
import string
import subprocess
import sys
import tempfile
import textwrap
import time
import warnings
from collections import defaultdict
from collections.abc import Callable, Iterable, Iterator, Sequence
from itertools import combinations, cycle, islice, product
from pathlib import Path
from typing import cast

TMP_DIR = (
    Path(tempfile.gettempdir()) / "fiddlesticks"
)  # Tests set an env var which gettempdir searches
TMP_DIR.mkdir(exist_ok=True)
DEFAULT_PROGRESS_FILE = TMP_DIR / "fiddlesticks_progress.json"
IS_WINDOWS = sys.platform == "win32"


SHIFT_MAP: dict[str, str] = {
    "1": "!",
    "2": '@"',
    "3": "#£",
    "4": "$",
    "5": "%",
    "6": "^",
    "7": "&",
    "8": "*",
    "9": "(",
    "0": ")",
    "-": "_",
    "=": "+",
    "[": "{",
    "]": "}",
    "\\": "|",
    ";": ":",
    "'": "@",
    ",": "<",
    ".": ">",
    "/": "?",
    "#": "~",
    "`": "~",
}

for c in string.ascii_lowercase:
    SHIFT_MAP[c] = c.upper()

LEET_SPEAK: dict[str, str] = {
    "a": "4@",
    "e": "3",
    "i": "1",
    "o": "0",
    "s": "5",
    "t": "7",
    "b": "8",
    "g": "9",
}

for c, v in list(LEET_SPEAK.items()):
    LEET_SPEAK[c.upper()] = v


def print_to_stderr(*objects, **kwargs):
    """Simple wrapper to print to stderr instead of stdout,
    for easy piping (of other output) to stdout.
    """
    print(*objects, file=sys.stderr, **kwargs)


def _calculate_total_from_alts_lengths(lengths, M):
    # dp[j] = sum of products for choosing j items
    dp = [0] * (M + 1)
    dp[0] = 1

    for length in lengths:
        for j in range(M, 0, -1):
            dp[j] += dp[j - 1] * length

    return dp[M]


def _combine_maps(
    subs_maps: Iterable[dict[str, str]],
) -> defaultdict[str, list[str]]:

    bi_map: defaultdict[str, list[str]] = defaultdict(list)
    for subs_map in subs_maps:
        for k, v in subs_map.items():
            bi_map[k].extend(v)
            for c in v:
                bi_map[c].append(k)
    return bi_map


SHIFT_AND_LEET_BI_MAP = _combine_maps([SHIFT_MAP, LEET_SPEAK])


def _all_positions_and_alts(
    num_subs: int,
    char_indexed_alts: dict[int, list[str]],
) -> Iterator[dict[int, list[str]]]:
    for positions in combinations(char_indexed_alts, num_subs):
        yield {i: char_indexed_alts[i] for i in positions}


def _candidate_from_selected_alts(
    guess: str,
    selected: Sequence[str],
    positions_and_alts: dict[int, list[str]],
) -> str:
    candidate = list(guess)
    for i, replacement in zip(positions_and_alts, selected):
        candidate[i] = replacement
    return "".join(candidate)


def _candidates_from_num_subs(
    guess: str,
    num_subs: int,
    char_indexed_alts: dict[int, list[str]],
    first_index: int = 0,
) -> Iterator[tuple[str, int]]:
    if num_subs == 0:
        yield guess, 0
        return
    num_skipped_or_yielded = 0
    for positions_and_alts in _all_positions_and_alts(num_subs, char_indexed_alts):
        n = math.prod(len(alts) for alts in positions_and_alts.values())
        if first_index >= num_skipped_or_yielded + n:
            num_skipped_or_yielded += n
            continue

        start = max(0, first_index - num_skipped_or_yielded)
        num_skipped_or_yielded += start

        # base iterator (product(*...) ) yields n
        # islice yields n - (first_index - num_skipped_or_yielded)
        # after the first iteration start is non-zero,
        # num_skipped_or_yielded == first_index
        # +=s to  => first_index + n - (firstindex - num_skipped_or_yielded) == n + num_skipped_or_yielded
        # so therefore first_index - num_skipped_or_yilded == first_index - prev - n
        # And from the prior continue check we know first_index < prev + n
        # Thereafter, first_index - prev - n < 0, and so start is only ever non-zero once.

        for selected in islice(
            product(*positions_and_alts.values()),
            start,
            None,  # stop
        ):
            yield (
                _candidate_from_selected_alts(guess, selected, positions_and_alts),
                num_subs,
            )

            num_skipped_or_yielded += 1


# https://docs.python.org/3/license.html#zero-clause-bsd-license-for-code-in-the-python-documentation
# https://docs.python.org/3/library/itertools.html#itertools-recipes
def roundrobin(*iterables):
    "Visit input iterables in a cycle until each is exhausted."
    # roundrobin('ABC', 'D', 'EF') → A D E B F C
    # Algorithm credited to George Sakkis
    iterators = map(iter, iterables)
    for num_active in range(len(iterables), 0, -1):
        iterators = cycle(islice(iterators, num_active))
        yield from map(next, iterators)


# def _candidates_from_alts_dict(
#     guesses_alts: dict[str, dict[int, list[str]]],
#     first_index: int = 0,
#     num_subs: int,
# ) -> Iterator[tuple[str, int]]:
#     iterators = (
#         _candidates_from_num_subs(guess, num_subs, alts)
#         for guess, alts in guesses_alts.items()
#     )
#     yield from roundrobin(iterators)


def _roundrobin_all_guesses(
    num_subs: int,
    guesses_alts: dict[str, dict[int, list[str]]],
    guesses_sub_totals: dict[str, int],
    first_index: int = 0,
) -> Iterator[tuple[str, int]]:

    num_skipped = num_skipped_per_unexhausted_iterator = smallest_iterator_length = 0

    iterator_lengths = sorted((n, i) for i, n in enumerate(guesses_sub_totals.values()))
    # Add items yielded by Round Robin, allowing for removal of exhausted iterators
    while iterator_lengths:
        prev_smallest_iterator_length = smallest_iterator_length
        smallest_iterator_length = iterator_lengths[0][0]
        num_left_in_shortest = smallest_iterator_length - prev_smallest_iterator_length
        L = len(iterator_lengths)
        num_skipped_this_block = num_left_in_shortest * L
        if first_index < num_skipped + num_skipped_this_block:
            break
        while iterator_lengths and iterator_lengths[0][0] == smallest_iterator_length:
            iterator_lengths.pop(0)

        num_skipped += num_skipped_this_block
        num_skipped_per_unexhausted_iterator += num_left_in_shortest

    first_index_this_block = first_index - num_skipped
    iterator_indices_this_block = sorted(i for n, i in iterator_lengths)
    iterators = []
    L = len(iterator_lengths)

    if L == 0:
        return iter([])

    index_into_iterator, index_of_iterator = divmod(first_index_this_block, L)
    index_into_iterator += num_skipped_per_unexhausted_iterator

    # j is only a loop variable to label the
    # up to L new iterators in the first RoundRobin state
    for j in range(index_of_iterator, L):
        guess_index = iterator_indices_this_block[j]
        guess = list(guesses_sub_totals)[guess_index]
        guess_it_length = guesses_sub_totals[guess]

        iterators.append(
            _candidates_from_num_subs(
                guess,
                num_subs,
                guesses_alts[guess],
                first_index=index_into_iterator,
            )
        )

    for j in range(index_of_iterator):
        # What if + j  goes over into a new block, and expires an iterator?

        # Just:
        # i) iterate over iterators in the cycle,
        # ii) skip those that have been exhausted,

        guess_index = iterator_indices_this_block[j]
        guess = list(guesses_sub_totals)[guess_index]
        guess_it_length = guesses_sub_totals[guess]

        # Skip if the offset wraps into next block, but the iterator
        # was already exhausted in this block.
        #
        # num_skipped + num_skipped_this_block is the first index in the next block
        # and the last iterator's offset from the first (0) could be + L-1
        if (
            first_index > num_skipped + num_skipped_this_block - L
            and guess_it_length == smallest_iterator_length  # was exhausted this block
        ):
            continue
        iterators.append(
            _candidates_from_num_subs(
                guess,
                num_subs,
                guesses_alts[guess],
                # These earlier iterators are in their next round robin cycle, so +1
                first_index=index_into_iterator + 1,
            )
        )

    return roundrobin(*iterators)


def _make_guesses_alt_chars(
    guesses: list[str],
    alt_char_map: dict[str, list[str]] = SHIFT_AND_LEET_BI_MAP,
) -> dict[str, dict[int, list[str]]]:
    return {
        guess: {
            #  list() in case alt_char_map[c] is a str
            i: list(alt_char_map[c])
            for i, c in enumerate(guess)
            if c in alt_char_map
        }
        for guess in guesses
    }


def _calculate_sub_totals(
    guesses_alts: dict[str, dict[int, list[str]]],
    min_subs: int = 0,
    max_subs: int = 2,
) -> dict[int, dict[str, int]]:

    lengths = {
        guess: [len(chars) for chars in alts.values()]
        for guess, alts in guesses_alts.items()
    }
    d = {}
    for num_subs in range(min_subs, max_subs + 1):
        sub_d = {
            guess: _calculate_total_from_alts_lengths(alts_lengths, num_subs)
            for guess, alts_lengths in lengths.items()
        }
        if sum(sub_d.values()) >= 1:
            d[num_subs] = sub_d

    return d


def _candidates_from_first_index(
    first_index: int,
    sub_totals: dict[int, dict[str, int]],
    guesses_alts: dict[str, dict[int, list[str]]],
) -> Iterator[tuple[str, int]]:
    num_skipped = 0
    for num_subs, d in sub_totals.items():
        sub_total = sum(d.values())
        if first_index >= num_skipped + sub_total:
            num_skipped += sub_total
            continue
        yield from _roundrobin_all_guesses(
            num_subs=num_subs,
            guesses_alts=guesses_alts,
            guesses_sub_totals=d,
            first_index=first_index - num_skipped,
        )
        first_index = 0


def candidate_passwords_from_alt_chars(
    guesses: list[str],
    first_index: int = 0,
    min_subs: int = 0,
    max_subs: int = 2,
    alt_char_map: defaultdict[str, list[str]] = SHIFT_AND_LEET_BI_MAP,
) -> tuple[int, Iterator[tuple[str, int]]]:

    if not guesses:
        return 0, iter([])

    guesses_alts = _make_guesses_alt_chars(guesses, alt_char_map)

    sub_totals = _calculate_sub_totals(guesses_alts, min_subs, max_subs)
    total_num_candidates = (
        sum(sum(guess_totals.values()) for guess_totals in sub_totals.values())
        - first_index
    )

    candidates = _candidates_from_first_index(
        first_index=first_index,
        sub_totals=sub_totals,
        guesses_alts=guesses_alts,
    )

    return total_num_candidates, candidates


def handle_found_password_output(
    password: str,
    i: int,
    t: float | None = None,
    print_passwords: bool = False,
    output_file: str = "",
    **kwargs,
):
    msg = f"\nFound password (candidate index: {i})"
    if t is not None:
        msg = f"{msg} in {t:.3f} seconds"
    print_to_stderr(msg, end="")

    if print_passwords:
        print_to_stderr(f" {password=}")

    if output_file:
        with open(output_file, "at") as f:
            f.write(password)


def make_py7zr_checker(archive: str, extract_to: str | None = None, **kwargs):
    from _lzma import LZMAError

    import py7zr
    from py7zr.exceptions import Bad7zFile, PasswordRequired

    if extract_to is None:
        extract_to = str(_make_new_tmp_sub_dir_for_7z(archive))
    stream = io.BytesIO(Path(archive).read_bytes())

    def is_correct_password_for_7z_file(candidate: str) -> bool:
        stream.seek(0)
        try:
            f = py7zr.SevenZipFile(stream, "r", password=candidate)
            f.extractall(path=extract_to)
        except (PasswordRequired, Bad7zFile, LZMAError):
            return False
        f.close()
        return True

    return is_correct_password_for_7z_file


def make_subprocess_checker(*args: str, **kwargs):

    # If args[-1][-1] = " ", it will get escaped
    # and quoted together with the appended password.
    # Interpreting that space as a Bash word separator
    # requires shell=True.
    # On the other hand, if last == "-p", e.g. with 7z,
    # the password is expected with no space separating it
    # from the -p.
    # Therefore to honour our contract of "any partial
    # Bash command to which a password guess can be appended"
    # it's easiest to use a single string (instead of an args list),
    # and (unless on Windows) shell=True.

    def checker(candidate: str) -> bool:
        result = subprocess.run(
            f"{' '.join(args)}{candidate}",
            capture_output=True,
            check=False,
            shell=not IS_WINDOWS,
        )
        return result.returncode == 0

    return checker


def _make_new_tmp_sub_dir(tmp_dir, name: str = "extracted") -> Path:
    i = -1
    suffix = ""
    while (p := tmp_dir / f"{name}{suffix}").is_dir():
        i += 1
        suffix = f"_{i}"
    p.mkdir(parents=True, exist_ok=False)
    return p


def _make_new_tmp_sub_dir_for_7z(file: str, tmp_dir: Path = TMP_DIR) -> Path:
    p = _make_new_tmp_sub_dir(tmp_dir)
    print_to_stderr(f"If {file} is unzipped successfully, contents will be in: {p}")
    return p


def make_7zip_checker(file: str, extract_to: str | None = None, **kwargs):

    # Ensure we can run 7zip in a subprocess.
    subprocess.run(["7z", "--help"], capture_output=True, check=True)

    if extract_to is None:
        extract_to = str(_make_new_tmp_sub_dir_for_7z(file))

    return make_subprocess_checker("7z", "x", f"-o{extract_to}", file, "-p")


def make_password_candidate_piper(*args, **kwargs):
    def piper(password: str):
        print(password, file=sys.stdout)
        return False

    return piper


PERSISTENT_7Z_CHECKER_OUTLINE = """\
#!/usr/bin/env bash

while read -r line; do
    # Silently run command, only check exit code
    7z x -o{extract_to} {file} -p"$line" > /dev/null 2>&1
    if [ $? -eq 0 ]; then
        echo "Success! :)"
        break
    fi
    echo "Nope :("
done
"""


def make_persistent_7zip_checker(file: str, extract_to: str | None = None, **kwargs):
    if extract_to is None:
        extract_to = str(_make_new_tmp_sub_dir_for_7z(file))

    cmd = textwrap.dedent(
        PERSISTENT_7Z_CHECKER_OUTLINE.format(extract_to=extract_to, file=file)
    )

    # Launch a single persistent Bash process reading from stdin line-by-line
    proc = subprocess.Popen(
        ["bash", "-c", cmd],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        text=True,
        bufsize=1,  # Line buffered
    )

    stdin = cast(io.TextIOBase, proc.stdin)
    stdout = cast(io.TextIOBase, proc.stdout)

    def checker(candidate: str) -> bool:
        # Send data down the pipe
        stdin.write(f"{candidate}\n")
        stdin.flush()

        # Read the response back
        response = stdout.readline().strip()
        return "Success" in response

    @atexit.register
    def cleanup():
        stdin.close()
        proc.wait()

    return checker


def make_py_avdu_aegis_checker(file: str, **kwargs):

    from py_avdu.encrypted_classes import VaultEncrypted

    vault_dict = json.loads(Path(file).read_text())

    encrypted = VaultEncrypted(**vault_dict)

    def checker(candidate: str) -> bool:
        try:
            encrypted.find_master_key(candidate)
            return True
        except ValueError:
            return False

    return checker


def make_pykeepass_checker(file: os.PathLike, **kwargs):

    from pykeepass import PyKeePass
    from pykeepass.exceptions import CredentialsError

    stream = io.BytesIO(Path(file).read_bytes())

    def checker(candidate: str) -> bool:
        try:
            PyKeePass(stream, password=candidate)
            return True
        except CredentialsError:
            return False

    return checker


def _get_hopefully_incorrect_password() -> str:
    try:
        return getpass.getuser()
    except OSError:
        return "password123"


def _try_make_ssh_key_checker_from_loader(
    loader,
    incorrect_password_msg: str,
    file: os.PathLike,
    **kwargs,
) -> Callable[[str], bool]:

    private_key_data = Path(file).read_bytes()
    hopefully_incorrect_password = _get_hopefully_incorrect_password()
    try:
        loader(private_key_data, password=hopefully_incorrect_password.encode())
    except ValueError as e:
        if e.args[0] != incorrect_password_msg:
            raise
    else:
        handle_found_password_output(
            hopefully_incorrect_password,
            i=-12345,
            t=None,
            **kwargs,
        )
        sys.exit(0)

    def checker(candidate: str) -> bool:
        try:
            loader(
                private_key_data,
                password=candidate.encode(),
                # Fail fast.  Key pair validation is out of scope
                # (but on success we do it anyway to give the user a heads up).
                # https://cryptography.io/en/latest/hazmat/primitives/asymmetric/serialization/#cryptography.hazmat.primitives.serialization.load_ssh_private_key
                unsafe_skip_rsa_key_validation=True,
            )
        except ValueError:
            return False
        loader(
            private_key_data,
            password=candidate.encode(),
            # Validate key pair, only once we already know
            # we have the correct password.
            unsafe_skip_rsa_key_validation=False,
        )
        return True

    return checker


def make_ssh_key_checker(file: os.PathLike, **kwargs):

    exceptions = []

    for factory in [
        make_openSSH_key_checker,
        make_ssh_pem_key_checker,
    ]:
        try:
            return factory(file, **kwargs)
        except ValueError as e:
            exceptions.append(e)

    raise ExceptionGroup(
        (
            f"Could not find valid SSH key loader for {file=}. "
            "Is it corrupted or in the incorrect format?"
        ),
        exceptions,
    )


def make_openSSH_key_checker(file: os.PathLike, **kwargs):
    from cryptography.hazmat.primitives.serialization import load_ssh_private_key

    return _try_make_ssh_key_checker_from_loader(
        load_ssh_private_key,
        "Corrupt data: broken checksum",  # Defined in cryptography's ssh.py, since 2020
        file,
        **kwargs,
    )


def make_ssh_pem_key_checker(file: os.PathLike, **kwargs):
    from cryptography.hazmat.primitives.serialization import load_pem_private_key

    return _try_make_ssh_key_checker_from_loader(
        load_pem_private_key,
        "Incorrect password, could not decrypt key",  # Defined in cryptography's Rust extension since Apr 2025
        # TODO: Investigate the other error strings that have been seen.  See misc_tests.py
        file,
        **kwargs,
    )


def make_MS_Office_files_key_checker(file: os.PathLike, **kwargs):

    import msoffcrypto
    import msoffcrypto.exceptions

    encrypted = io.BytesIO(Path(file).read_bytes())
    office_file = msoffcrypto.OfficeFile(encrypted)

    stream = io.BytesIO()

    def checker(candidate: str) -> bool:
        office_file.load_key(password=candidate)
        try:
            office_file.decrypt(stream)
            return True
        except msoffcrypto.exceptions.InvalidKeyError:
            return False

    return checker


def make_Veracrypt_checker(file: os.PathLike, **kwargs):

    path = Path(file).resolve()
    assert path.is_file()

    # Ensure we can run Veracrypt in a subprocess.
    subprocess.run(["veracrypt", "--help"], capture_output=True, check=True)

    temp_dir = tempfile.TemporaryDirectory(delete=False)

    mount_point = _make_new_tmp_sub_dir(
        tmp_dir=Path(temp_dir.name) / "mnt",
        name="veracrypt_volume",
    ).resolve()

    args = [
        "veracrypt",
        "--text",
        "--non-interactive",
        "--keyfiles=",
        "--pim=0",
        "--protect-hidden=no",
        "--mount",
        path.as_posix(),
        mount_point.as_posix(),
        "--password=",
    ]

    @atexit.register
    def cleanup():
        subprocess.run(["veracrypt", "--unmount"], capture_output=True, check=True)
        temp_dir.cleanup()

    return make_subprocess_checker(*args)


def save_ruled_out_indices_to_progress_file(
    indices: list[int],
    saved_progress_file: Path = DEFAULT_PROGRESS_FILE,
):
    saved_indices: list[int]
    if saved_progress_file.is_file():
        saved_indices = json.loads(saved_progress_file.read_text())[
            "ruled_out_candidates_indices"
        ]
    else:
        saved_indices = []

    saved_indices.extend(indices)
    saved_indices.sort()

    # Drop any initial sequence of consecutive indices
    # (we assume all consecutive ones below the lowest saved one
    #  have all been rules out)
    i = 0
    while i + 1 < len(saved_indices) and saved_indices[i + 1] <= saved_indices[i] + 1:
        i += 1
    del saved_indices[:i]

    saved_progress_file.write_text(
        json.dumps({"ruled_out_candidates_indices": saved_indices})
    )


def offer_to_skip_indices_ruled_out_by_progress_file(
    force_resume: bool = False,
    saved_progress_file: Path = DEFAULT_PROGRESS_FILE,
) -> int:
    resume_from = None
    progress_text = saved_progress_file.read_text()

    # Clear previous session's progress.  We've done all we can with it now.
    saved_progress_file.unlink()
    try:
        progress_dict = json.loads(progress_text)
        ruled_out = sorted(progress_dict["ruled_out_candidates_indices"])
        # Could search through ruled_out
        # to find the lowest index that's not ruled out (that's higher
        # than the lowest one that is).
        resume_from = ruled_out[0] + 1
    except (json.decoder.JSONDecodeError, KeyError, IndexError, TypeError):
        pass
    if resume_from is not None:
        print_to_stderr(f"Found previous progress in {saved_progress_file}. ")
        if (
            force_resume
            or input(
                f"Start from index {resume_from} read from this file? (y/n) "
            ).lower()
            == "y"
        ):
            save_ruled_out_indices_to_progress_file([ruled_out[0]], saved_progress_file)
            return resume_from
    return 0


def check_passwords_sequentially(
    candidates: Iterable[tuple[str, int]],
    test_func: Callable[[str], bool],
    verbosity: int = 0,
    update_every: int | None = None,
    total: int | None = None,
    print_passwords: bool = False,
    first_index: int = 0,
    **kwargs,
) -> tuple[str, int] | None:

    out_of_total = "" if total is None else f"/{total - 1}"  # Highest index

    if update_every is None:
        update_every = 40 if total is None else max(1, total // 300)

    if verbosity >= 1:
        update_every = min(update_every, 1000)

    last_printed_num_subs = 0
    for i, (candidate, num_subs) in enumerate(candidates, start=first_index):
        if test_func(candidate):
            return candidate, i

        save_ruled_out_indices_to_progress_file([i])

        if i % update_every:
            continue
        if verbosity == 0:
            print_to_stderr(".", end="", flush=True)
            # If testing multiple guesses at the same time, the current
            # number of substitutions for each might not be synchronised.
            if num_subs > last_printed_num_subs:
                print_to_stderr(
                    f"Now testing candidates formed by {num_subs} substitutions from guess"
                )
                last_printed_num_subs = num_subs
        elif verbosity >= 2 and print_passwords:
            print_to_stderr(
                f"{i}{out_of_total}) tried: {candidate} (num substitutions={num_subs})",
                flush=True,
            )
        else:
            # verbosity == 1 or (verbosity ==2 and not print_passwords)
            print_to_stderr(
                f"{i}{out_of_total}, num substitutions={num_subs}", flush=True
            )

    return None


default_password_protected_file_checker_factories = {
    ".7z": make_7zip_checker,
    ".json": make_py_avdu_aegis_checker,
    ".kdbx": make_pykeepass_checker,
    ".kdb": make_pykeepass_checker,
    ".pem": make_ssh_key_checker,  # could make this the legacy PEM one?
    ".key": make_ssh_key_checker,
    ".priv": make_ssh_key_checker,
    ".docx": make_MS_Office_files_key_checker,
    ".xlsx": make_MS_Office_files_key_checker,
    ".hc": make_Veracrypt_checker,
    ".tc": make_Veracrypt_checker,
}


def _default_factory_selector(*args: str):
    if not args:
        raise ValueError(
            "Default checker requires arg(s) to define how to test the passwords"
        )

    path = Path(args[0])

    if len(args) == 1 and path.is_file():
        return default_password_protected_file_checker_factories[path.suffix.lower()]

    return make_subprocess_checker


parser = argparse.ArgumentParser(prog="fiddlesticks")
parser.suggest_on_error = True  # type: ignore
parser.add_argument(
    "--new-search",
    action="store_true",
    help=(
        "Don't offer to resume a previous interrupted search from saved progress (if available). "
    ),
)
parser.add_argument(
    "--resume",
    "-y",
    action="store_true",
    help=("Always resume a previous interrupted search when possible. "),
)
parser.add_argument(
    "--first-index",
    type=int,
    default=None,
    help=("First index of candidate to start checking from. "),
)
parser.add_argument(
    "--max-subs",
    "-N",
    type=int,
    default=2,
    help=(
        "The maximum number of character substitutions "
        "that will be applied to the guess.  Default: 2"
    ),
)
parser.add_argument(
    "--min-subs",
    type=int,
    default=0,
    help=(
        "The minimum number of character substitutions "
        "that will be applied to the guess. Default: 0"
    ),
)
parser.add_argument("--verbosity", "-v", action="count", default=0)
parser.add_argument(
    "--update-every",
    "-V",
    type=int,
    default=None,
    help=(
        "How many candidates to test before printing an update message "
        "to stderr (no effect without -v). "
    ),
)
parser.add_argument(
    "--output-file",
    "-o",
    type=str,
    default="",
    help="File to write found passwords to.",
)
parser.add_argument(
    "--print-passwords",
    "-P",
    action="store_true",
    help=(
        "Set this option to print passwords to stderr. "
        "By default, neither found passwords (nor candidates if -vv) are printed. "
        "E.g. if extracting a password-protected archive as a side-effect is sufficient "
        "(and you intend to re-encrypt it with a different password anyway)."
    ),
)
parser.add_argument(
    "--password-guess",
    "-p",
    action="append",
    dest="password_guesses",
    default=[],
    help=(
        "WARNING! Password guesses given on the command line may be saved by your shell, "
        "and e.g. appear in the Bash history file.  Otherwise, you will be prompted to "
        "securely enter the guess(es) before the search can begin. "
    ),
)
parser.add_argument(
    "--input-file",
    "-i",
    required=False,
    type=Path,
    help="Optional file of password guesses. ",
)
parser.add_argument(
    "--extract-to",
    "-x",
    default=None,
    help=(
        "The dir to try to extract archives in "
        "(if using an external program as the password checker)"
    ),
)
parser.add_argument(
    "extras",
    type=str,
    nargs="*",
    action="extend",
    help=(
        "Extra args to create the password checker with. "
        "E.g. file to find password for, "
        "or partial shell command, "
        "to which the password guesses will be appended, "
        "such as: 7z x archive.7z -p"
    ),
)

parser.set_defaults(
    command=None,
    password_generator=candidate_passwords_from_alt_chars,
    alt_char_map=None,
)


def add_mutex_group(
    title: str | None = None,
    description: str | None = None,
    required: bool = False,
):
    arg_group = parser.add_argument_group(title=title, description=description)
    mutex_arg_group = arg_group.add_mutually_exclusive_group(required=required)
    return mutex_arg_group


command_args_group = add_mutex_group(
    "Sub-command",
    (
        "The sub-commmand (if any), e.g. the Password checker to use to test candidates. "
        "If not set, the sub-command is inferred from the file extension "
        "of any archive file (if present). "
        "Otherwise a partial external shell command is expected, to which candidates can be appended. "
    ),
)


def add_command_arg(name, command, help: str | None = None):
    command_args_group.add_argument(
        name,
        dest="command",
        action="store_const",
        const=command,
        help=help,
    )


add_command_arg("--shell", make_subprocess_checker)
add_command_arg("--7zip", make_7zip_checker)
add_command_arg("--7zip-persistent", make_persistent_7zip_checker)
add_command_arg(
    "--pipe",
    make_password_candidate_piper,
    help=(
        "Print all password candidates to stdout, "
        "e.g. to pipe them to an external password checking program. "
        "Overrides --print-passwords. "
    ),
)
add_command_arg("--print-char-map", "print-char-map")
# Optional commands requiring extra deps
add_command_arg("--ssh", make_ssh_key_checker)
add_command_arg("--openssh", make_openSSH_key_checker)
add_command_arg("--ssh-pem", make_ssh_pem_key_checker)
add_command_arg("--keypassxc", make_pykeepass_checker)
add_command_arg("--aegis", make_py_avdu_aegis_checker)
add_command_arg("--py7zr", make_py7zr_checker)
add_command_arg("--msoffice", make_MS_Office_files_key_checker)
add_command_arg("--veracrypt", make_Veracrypt_checker)


alt_char_map_group = add_mutex_group(
    "Character map",
    (
        "The mapping for alternative characters, "
        "to be used to generate candidate passwords from. "
    ),
)

alt_char_map_group.add_argument(
    "--shift_and_leet",
    dest="alt_char_map",
    action="store_const",
    const=SHIFT_AND_LEET_BI_MAP,
)

alt_char_map_group.add_argument(
    "--char-map",
    type=Path,
    help=(
        "A JSON file containing a mapping of characters "
        "(length 1 strings) to alternative characters."
    ),
)


def cli(args: list[str] = sys.argv[1:]) -> int:

    if not args:
        parser.print_help(file=sys.stderr)
        return 0

    ns = parser.parse_args(args)
    kwargs = vars(ns).copy()

    alt_char_map: defaultdict[str, list[str]]
    if ns.alt_char_map is None:
        if ns.char_map is not None:
            alt_char_map = defaultdict(list)
            alt_char_map.update(json.loads(ns.char_map.read_text()))
        else:
            alt_char_map = SHIFT_AND_LEET_BI_MAP
    else:
        alt_char_map = ns.alt_char_map

    if ns.command == "print-char-map":
        # Prettified JSON, without adding a new line for each item in an array
        # (unlike json.dumps(..., indent = 4))
        items = iter(alt_char_map.items())
        k, v = next(items)
        print_to_stderr("{" + f"{json.dumps(k)}: {json.dumps(v)}", end="")
        for k, v in items:
            print_to_stderr(f",\n {json.dumps(k)}: {json.dumps(v)}", end="")
        print_to_stderr("\n}")
        return 0

    password_guesses = kwargs.pop("password_guesses", [])

    if password_guesses:
        warnings.warn(
            "Password guesses given on command line may be stored in history. "
            "After this program ends, you may wish to delete the latest history entry, "
            "e.g. by running: history -d $(history 1 | awk '{print $1}')"
        )

    input_file = kwargs.pop("input_file", None)
    if input_file is not None:
        password_guesses.extend(input_file.read_text().splitlines())

    if not password_guesses:
        while password_guess := getpass.getpass(
            "Input password guess (or press Enter when done): "
        ):
            password_guesses.append(password_guess)

    extras = kwargs.pop("extras")
    new_search = kwargs.pop("new_search")
    force_resume = kwargs.pop("resume")
    first_index: int | None = kwargs.pop("first_index")

    if DEFAULT_PROGRESS_FILE.is_file():
        if not new_search and first_index is None:
            first_index = offer_to_skip_indices_ruled_out_by_progress_file(force_resume)
        else:
            DEFAULT_PROGRESS_FILE.unlink()

    if first_index is None:
        first_index = 0

    if ns.command is None:
        command = _default_factory_selector(*extras)
    else:
        command = ns.command

    if (
        command
        not in (
            make_7zip_checker,
            make_persistent_7zip_checker,
            make_subprocess_checker,
            make_password_candidate_piper,
        )
        and not ns.print_passwords
        and not ns.output_file
        and ns.verbosity == 0
    ):
        warnings.warn(
            "The SSH key, Keepass and the Aegis vault checkers do not decrypt files. "
            "When running fiddlesticks without print-passwords, without "
            "an output-file, and with verbosity=0, only the candidate index "
            "of any recovered password will be printed. "
        )

    total, candidates = ns.password_generator(
        first_index=first_index,
        guesses=password_guesses,
        min_subs=ns.min_subs,
        max_subs=ns.max_subs,
        alt_char_map=alt_char_map,
    )
    checker = command(*extras, **kwargs)

    t0 = time.time()

    result = check_passwords_sequentially(candidates, checker, total=total, **kwargs)

    t1 = time.time()

    if result is None:
        if ns.command is make_password_candidate_piper:
            return 0

        print_to_stderr(
            "\n\nCould not find password. Try a different guess, or increasing max substitutions (-N) ? "
        )
        if ns.verbosity >= 1:
            print_to_stderr(f"Search took: {t1 - t0:.3f} seconds")
        return 1

    password, i = result

    handle_found_password_output(password, i, t1 - t0, **kwargs)

    return 0


if __name__ == "__main__":
    cli()
