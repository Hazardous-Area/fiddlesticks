# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///

__version__ == "0.0.0"

import argparse
import collections
import functools
import io
import itertools
from pathlib import Path
from typing import Iterator, Iterable, Collection
from types import MappingProxyType


LEET_SPEAK = MappingProxyType({
    'a': '4@',
    'e': '3',
    'i': '1!',
    'o': '0',
    's': '5$',
    't': '7',
    'b': '8',
    'g': '9',
})

SHIFT_MAP = MappingProxyType({
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
    '`': '~',
})

def candidate_passwords_from_substitutions(
    guess: str,
    max_subs: int = 2,
    subs_maps: Iterable[dict[str,str]] = [LEET_SPEAK, SHIFT_MAP],
    ) -> Iterator[str]:
    
    yield guess

    multimaps = []
    for subs_map in subs_maps:
        multimap = collections.defaultdict(list)
        for k, v in subs_map.items:
            for c in v:
                multimap[k].append(c)
                multimap[c].append(k)
        multimaps.append(multimap)

    options = []
    for char in guess:
        opts = []
        for multimap in multimaps:
            alt_chars = multimap.get(char, None)
            if alt_chars is not None:
                opts.extend(alt_chats)

        options.append(opts)
    
    for num_subs in range(1, max_subs + 1):

        for positions in itertools.combinations(range(len(guess)), num_subs):

            pos_with_opts = [(i, options[i]) for i in positions if options[i]]
            
            if len(pos_with_opts) != num_subs:
                continue
            
            choices_per_pos = [opts for i, opts in pos_with_opts]
            
            for selected in itertools.product(*choices_per_pos):

                candidate_password = list(guess)
                for (i, _), replacement in zip(pos_with_opts, selected):
                    candidate_password[i] = replacement
                yield ''.join(candidate_password)


def make_7z_file_password_checker(archive: str = "test_py7zr.7z"):
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


def test_passwords(
    candidates: candidates[str],
    test_func: Callable[[str], bool],
    verbosity: int = 0,
    update_every: int = 1,
) -> tuple[tuple[str, int] | None, int]:
    
    N = len(candidates)
    for i, candidate in enumerate(candidates, start=1):
        if test_func(candidate):
            return (candidate, i), N
        if i % update_every:
            continue
        if verbosity == 0:
            print(".", end="", flush=True)
        elif verbosity >= 2:
            print(f"{i}/{N}) tried: {candidate}", flush=True)
        else:
            print(f"{i}/{N}", flush=True)
    return None, N
    

def search_for_passwords_from_guesses(
    guesses: Iterable[str],
    candidates_gen: Callable[[str], Iterator[str]],
    ) -> tuple[tuple[str, int] | None, int]:
    candidates = {
        candidate
        for guess in guesses
        for candidate in candidates_gen(guess)
    }
    return test_passwords(
        candidates,
        functools.partial(candidate_passwords_from_substitutions, max_subs=2),
        make_7z_file_password_checker(),
    )


def main() -> int:
    parser = argparse.ArgumentParser()


    namespace = parser.parse_args()

    result = 

    if result is None:
        print(f"\n\nCould not find password after {N} attempts.  Try increasing search bounds, or another guess? ")
        return 1

    password, i = result
    print(f"\n Found: {password=} (guess number: {i}/{N})")
    return 0

if __name__ == '__main__':
    main()