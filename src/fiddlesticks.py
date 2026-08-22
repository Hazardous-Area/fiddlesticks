# /// script
# requires-python = ">=3.12"
# dependencies = []
# optional_dependencies = []
# ///

__version__ = "0.0.0"

import argparse
import collections
import functools
import getpass
import io
import itertools
from pathlib import Path
import string
from typing import Iterator, Iterable, Collection, Hashable, Callable
import warnings



SHIFT_MAP = {
    '1': '!',
    '2': '@"',
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
    "'": '@',
    ',': '<',
    '.': '>',
    '/': '?',
    '#': '~',
    '`': '~',
}

for c in string.ascii_lowercase:
    SHIFT_MAP[c] = c.upper()

LEET_SPEAK = {
    'a': '4@',
    'e': '3',
    'i': '1',
    'o': '0',
    's': '5',
    't': '7',
    'b': '8',
    'g': '9',
}

for c, v in list(LEET_SPEAK.items()):
    LEET_SPEAK[c.upper()] = v


def _calculate_total(lengths, M):
    # dp[j] = sum of products for choosing j items
    dp = [0] * (M + 1)
    dp[0] = 1
    
    for length in lengths:
        for j in range(M, 0, -1):
            dp[j] += dp[j-1] * length
    
    return dp[M]


def _combine_maps[T: Hashable](
    subs_maps: Iterable[dict[T,Iterable[T]]],
    ) -> dict[T,list[T]]:

    bi_map = collections.defaultdict(list)
    for subs_map in subs_maps:
        for k, v in subs_map.items():
            bi_map[k].extend(v)
            for c in v:
                bi_map[c].append(k)
    return bi_map


BI_MAP = _combine_maps([SHIFT_MAP, LEET_SPEAK])


def candidate_passwords_from_alt_chars(
    guess: str,
    max_subs: int = 2,
    alt_chars: list[list[str]] | None = None,
    ) -> tuple[int, Iterator[str]]:
    

    alt_chars = alt_chars or [BI_MAP[c] for c in guess]
    
    lengths = [len(chars) for chars in alt_chars] 
    total_num_candidates = sum(_calculate_total(lengths, M) for M in range(1, max_subs+1))
    
    def generator():
        yield guess

        for num_subs in range(1, max_subs + 1):

            for positions in itertools.combinations(range(len(guess)), num_subs):

                pos_with_opts = [(i, alt_chars[i]) for i in positions if alt_chars[i]]
                
                if len(pos_with_opts) != num_subs:
                    continue
                
                choices_per_pos = [opts for i, opts in pos_with_opts]
                
                for selected in itertools.product(*choices_per_pos):

                    candidate_password = list(guess)
                    for (i, _), replacement in zip(pos_with_opts, selected):
                        candidate_password[i] = replacement
                    yield ''.join(candidate_password)

    return total_num_candidates, generator()


def make_py7zr_file_password_checker(archive: str):
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


def make_subprocess_checker(*args: str):
    
    def is_correct_password(password: str) -> bool:
        result = subprocess.run(f"{command}{password}")
        return result.returncode==0
    return is_correct_password

def make_7zip_subprocess_checker(file: str):
    return make_subprocess_checker(f"7z x {file} -p")

def test_passwords_sequentially(
    candidates: Iterable[str],
    test_func: Callable[[str], bool],
    verbosity: int = 0,
    update_every: int = 1,
    total: int | None = None,
    print_password_to_stdout: bool = False
) -> tuple[str, int] | None:
    
    out_of_total = "" if total is None else f"/{total}"

    for i, candidate in enumerate(candidates, start=1):
        if test_func(candidate):
            return candidate, i

        if i % update_every:
            continue
        if verbosity == 0:
            print(".", end="", flush=True)
        elif verbosity >= 2 and print_passwords:
            print(f"{i}{out_of_total}) tried: {candidate}", flush=True)
        else:
            print(f"{i}{out_of_total}", flush=True)

    return None


default_password_protected_file_checker_factories = {
    ".7z" : make_7zip_subprocess_checker,
}


def default_checker_factory(*args: str):
    if not args:
        raise ValueError(
            "Default checker requires arg(s) to define how to test the passwords"
        )
    
    path = Path(args[0])

    if path.is_file():
        return default_password_protected_file_checker_factories[path.suffix.lower()](*args)
    
    return make_subprocess_checker(*args)


def try_find_password_sequentially(
    extras: list[str],
    password_guess: str,
    max_subs: int = 2,
    checker_factory: Callable[[str], Callable[[str], bool]] = make_subprocess_checker,
    password_generator: Callable[[str, int], tuple[int | None, Iterator[str]]] = candidate_passwords_from_alt_chars,
    **kwargs,
) -> tuple[str, int] | None:

    checker = checker_factory(*args)
    total, candidates = password_generator(password_guess, max_subs)
    return test_passwords_sequentially(candidates, checker, total=total, **kwargs)



parser = argparse.ArgumentParser()
parser.add_argument("--max-subs", '-N', type=int, default=2)
parser.add_argument("--password-guess", type=str, default="")
parser.add_argument('--verbosity', '-v', action='count', default=0)
parser.add_argument('--output-file', '-o', type=str, default="")
parser.add_argument('--print-password-to-stdout', '-p', action="store_true")
parser.add_argument(
    "extras",
    type=str,
    nargs="*",
    action="extend",
    help=("Extra args to create the password checker with. "
          "E.g. file to find password for, "
          "or partial shell command, "
          "to which the password guesses will be appended, "
          "such as: 7z x archive.7z -p"
    ),
)

parser.set_defaults(
    checker_factory=default_checker_factory,
    password_generator=candidate_passwords_from_alt_chars,
)


checker_factories_group = parser.add_mutually_exclusive_group(required=False)
def add_checker_factory_arg(name, checker_factory, help: str | None = None):
    checker_factories_group.add_argument(
        name,
        dest="checker_factory",
        action="store_const",
        const=checker_factory,
        help=help,
    )

password_generators_group = parser.add_mutually_exclusive_group(required=False)
def add_pwd_generator_arg(name, checker_factory, help: str | None = None):
    password_generators_group.add_argument(
        name,
        dest="password_generator",
        action="store_const",
        const=checker_factory,
        help=help,
    )




def cli() -> int:

    namespace = parser.parse_args()

    if namespace.password_guess:
        warnings.warn(
            "Password guess given on command line may be stored in history. "
            "After this program ends, to delete the entry, e.g.: "
            "history -d $(history 1 | awk '{print $1}')"
        )
    
    kwargs = vars(namespace).copy()
    
    if not namespace.password_guess:
        kwargs["password_guess"] = getpass.getpass("Input password guess: ")

    result = try_find_password_sequentially(**kwargs)

    if result is None:
        print(f"\n\nCould not find password.  Try a different guess, or increasing max substitutions (-N) ? ")
        return 1

    password, i = result
    msg = f"\n Found password (guess number: {i})"
    print(msg, end="")
    if namespace.print_password_to_stdout:
        print(f" {password=}")
    if namespace.output_file:
        with open(namespace.output_file, "at") as f:
            f.write(f"{msg}")
    return 0

if __name__ == '__main__':
    cli()