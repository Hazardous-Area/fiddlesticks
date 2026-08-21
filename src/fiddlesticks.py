# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///

__version__ == "0.0.0"

import argparse
import collections
import functools
import getpass
import io
import itertools
from pathlib import Path
import subprocess
from typing import Iterator, Iterable, Collection


LEET_SPEAK = {
    'a': '4@',
    'e': '3',
    'i': '1!',
    'o': '0',
    's': '5$',
    't': '7',
    'b': '8',
    'g': '9',
}

SHIFT_MAP = {
    '1': '!',
    '2': '@',
    '3': '#£',
    '4': '$',
    '5': '%',
    '6': '^',
    '7': '&',
    '8': '*',
    '9': '(',
    '0': ')',
    '-': '_',
    '=': '+',
    '[': '{',
    ']': '}',
    '\\': '|',
    ';': ':',
    "'": '"',
    ',': '<',
    '.': '>',
    '/': '?',
    '`': '¬~',
    '#': '~',
}

CASE_MAP = {
    c.lower(): c.upper() 
    for c in "abcdefghijklmnopqrstuvwxyz"
}



def candidate_passwords_from_substitutions(
    guesses: Collection[str],
    max_subs: int = 2,
    subs_maps: Iterable[dict[str,str]] = [LEET_SPEAK, SHIFT_MAP, CASE_MAP],
    ) -> Iterator[str]:    

    # Combined reversible map defining all possible alternative 
    # characters (alts) for each password character
    multimap = collections.defaultdict(list)
    for subs_map in subs_maps:
        for k, v in subs_map.items():
            for c in v:
                # add k's alt characters (to the list of any previous ones).
                multimap[k].append(c)
                # add k to each alt character's list of alts
                multimap[c].append(k)

    for guess in guesses:
        # Try the initial guess unaltered.
        yield guess

        L = len(guess)
        # A list of lists of the alts for each char in the guess
        # The sublists are not mutated, so we reuse the same one
        # just created in multimap (otherwise a .copy() should be made).
        guess_alts = [multimap.get(char, []) for char in guess]

        alts_indices = [i for i, alts in enumerate(guess_alts) if alts]

        # Consider candidate passwords formed by replacing
        # exactly num_subs characters in guess with their alt
        for num_subs in range(1, max_subs + 1):

            for indices in itertools.combinations(alts_indices, num_subs):
               
                alts_at_indices = [guess_alts[i] for i in indices]
                
                for alts in itertools.product(*alts_at_indices):
                    yield ''.join(
                        alts[i] if i in indices else guess[i]
                        for i in range(L)
                    )


def make_py7zr_file_password_checker(archive: str = "test_py7zr.7z"):
    import py7zr
    stream = io.BytesIO(Path(archive).read_bytes())
    def is_correct_password_for_7z_file(password: str, ) -> bool:
        stream.seek(0)
        try:
            f = py7zr.SevenZipFile(stream, 'r', password=password)
            f.extractall(path="extracted")
        except py7zr.exceptions.PasswordRequired:
            return False
        finally:
            f.close()
        return True
    return is_correct_password_for_7z_file

def make_subprocess_checker(command: str):
    def is_correct_password(password: str) -> bool:
        result = subprocess.run(f"{command}{password}")
        return result.returncode==0
    return is_correct_password

def test_passwords(
    candidates: Iterable[str],
    test_func: Callable[[str], bool],
    verbosity: int = 0,
    update_every: int = 1,
    out_of_total: str = "",
) -> tuple[str, int] | None:
    
    for i, candidate in enumerate(candidates, start=1):
        if test_func(candidate):
            return candidate, i

        if i % update_every:
            continue
        if verbosity == 0:
            print(".", end="", flush=True)
        elif verbosity >= 2:
            print(f"{i}{out_of_total}) tried: {candidate}", flush=True)
        else:
            print(f"{i}{out_of_total}", flush=True)

    return None


def default(
    command: str,
    password_guess: str,
    max_subs: int = 2,
) -> tuple[str, int] | None:

    checker = make_subprocess_checker(command)
    candidates = candidate_passwords_from_substitutions([password_guess], max_subs)
    return test_passwords(candidates, checker)



parser = argparse.ArgumentParser()
parser.add_argument("--max-subs", type=int, default=2)
parser.add_argument("--password-guess", type=str, default="")
parser.add_argument("shell_command", type=str, default="7z x archive.7z -p")

optional_modules_installed = {}

def cli() -> int:
    if sys.argv[1] in optional_modules_installed:
        pass
    else:
        namespace = parser.parse_args()
        password_guess = namespace.password_guess or getpass.getpass("Enter password guess:")
        result = default(password_guess = password_guess, **vars(namespace))


    if result is None:
        print(f"\n\nCould not find password after {N} attempts.  Try increasing search bounds, or another guess? ")
        return 1

    password, i = result
    print(f"\n Found: {password=} (guess number: {i}/{N})")
    return 0

if __name__ == '__main__':
    cli()