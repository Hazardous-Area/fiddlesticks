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
from typing import Iterator, Iterable, Collection
from types import MappingProxyType
import warnings


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
    shell_command: str,
    password_guess: str,
    max_subs: int = 2,
) -> tuple[str, int] | None:

    checker = make_subprocess_checker(shell_command)
    candidates = candidate_passwords_from_substitutions([password_guess], max_subs)
    return test_passwords(candidates, checker)



parser = argparse.ArgumentParser()
parser.add_argument("--max-subs", type=int, default=2)
parser.add_argument("--password-guess", type=str, default="")
parser.add_argument("shell_command", type=str, default="7z x archive.7z -p")
commands_group = parser.add_mutually_exclusive_group(required=False)

parser.set_defaults(command=default)

def add_command_arg(name, command, help: str | None = None):
    commands_group.add_argument(
        name,
        dest="command",
        action="store_const",
        const=command,
        help=help,
    )


def main() -> int:

    namespace = parser.parse_args()

    if namespace.password_guess:
        warnings.warn(
            "Password guess given on command line may be stored in history. "
            "After this program ends, to delete the entry, e.g.: "
            "history -d $(history 1 | awk '{print $1}')"
        )
    
    kwargs = vars(namespace)
    
    if not namespace.password_guess is None:
        kwargs["password_guess"] = getpass.getpass("Input password guess: ")

    result = ns.command(**kwargs)

    if result is None:
        print(f"\n\nCould not find password after {N} attempts.  Try increasing search bounds, or another guess? ")
        return 1

    password, i = result
    print(f"\n Found: {password=} (guess number: {i}/{N})")
    return 0

if __name__ == '__main__':
    main()