# /// script
# requires-python = ">=3.12"
# dependencies = []
# optional_dependencies = []
# ///

__version__ = "0.0.0"

import argparse
import atexit
import collections
import functools
import getpass
import io
import itertools
from pathlib import Path
import string
import subprocess
import sys
import tempfile
import textwrap
import time
from typing import Iterator, Iterable, Collection, Hashable, Callable
import warnings


TMP_DIR = Path(tempfile.gettempdir()) / "fiddlesticks"
TMP_DIR.mkdir(exist_ok=True)

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

def print_to_stderr(*objects, file=sys.stderr, **kwargs):
    """ Simple wrapper to print to stderr instead of stdout, 
        for easy piping to stdout. 
    """
    print(*objects, file=file, **kwargs)

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


SHIFT_AND_LEET_BI_MAP = _combine_maps([SHIFT_MAP, LEET_SPEAK])


def candidate_passwords_from_alt_chars(
    guess: str,
    max_subs: int = 2,
    alt_chars: list[list[str]] | None = None,
    alt_char_map: dict[str, list[str]] = SHIFT_AND_LEET_BI_MAP,
    ) -> tuple[int, Iterator[str]]:
    

    alt_chars = alt_chars or [alt_char_map[c] for c in guess]
    
    lengths = [len(chars) for chars in alt_chars] 
    total_num_candidates = sum(_calculate_total(lengths, M) for M in range(1, max_subs+1))
    
    def generator():
        yield guess

        for num_subs in range(1, max_subs + 1):

            for positions in itertools.combinations(range(len(guess)), num_subs):

                pos_with_opts = [alt_chars[i] for i in positions if alt_chars[i]]
                
                if len(pos_with_opts) != num_subs:
                    continue
                
                choices_per_pos = [opts for opts in pos_with_opts]
                
                for selected in itertools.product(*choices_per_pos):

                    candidate_password = list(guess)
                    for i, replacement in zip(positions, selected):
                        candidate_password[i] = replacement
                    yield ''.join(candidate_password)

    return total_num_candidates, generator()


def make_py7zr_checker(archive: str, extract_to: str | None = None, **kwargs):
    import py7zr
    if extract_to is None:
        extract_to = str(_make_new_tmp_sub_dir(archive))
    stream = io.BytesIO(Path(archive).read_bytes())
    def is_correct_password_for_7z_file(candidate: str, ) -> bool:
        stream.seek(0)
        try:
            f = py7zr.SevenZipFile(stream, 'r', password=candidate)
            f.extractall(path=extract_to)
        except (py7zr.exceptions.PasswordRequired, py7zr.exceptions.Bad7zFile):
            return False
        else:
            f.close()
        return True
    return is_correct_password_for_7z_file


def make_subprocess_checker(*args: str, **kwargs):
    *rest, last = args
    def is_correct_password(candidate: str) -> bool:
        result = subprocess.run([*rest, f"{last}{candidate}"], capture_output=True)
        return result.returncode==0
    return is_correct_password

def _make_new_tmp_sub_dir(file: str) -> Path:
    i = -1
    suffix = ""
    while (p := TMP_DIR / f"extracted{suffix}").is_dir():
        i += 1
        suffix = f"_{i}"
    p.mkdir()
    print_to_stderr(f"If {file} is unzipped successfully, contents will be in: {p}")
    return p

class ProgramNotFound(Exception): pass

def make_7zip_checker(file: str, extract_to: str | None = None, **kwargs):
    args = ["7z", "--help"]
    result =subprocess.run(args, capture_output=True)
    if result.returncode != 0:
        raise ProgramNotFound(f"7zip.  Args: {args}")

    if extract_to is None:
        extract_to = str(_make_new_tmp_sub_dir(file))

    return make_subprocess_checker("7z","x", f"-o{extract_to}", file, "-p")

def make_password_candidate_piper(**kwargs):
    def piper(password: str):
        print(password, file=sys.stdout)
        return False
    return piper

def make_persistent_7zip_checker(file: str, extract_to: str | None = None, **kwargs):
    if extract_to is None:
        extract_to = str(_make_new_tmp_sub_dir(file))

    cmd = textwrap.dedent(f"""\
    while read -r line; do
    
    # Silently run command, only check exit code
    7z x -o{extract_to} {file} -p"$line" > /dev/null 2>&1
    if [ $? -eq 0 ]; then
        echo "Success! :)"
        break
    fi
    echo "Nope :("
    done
    """)

    # Launch a single persistent Bash process reading from stdin line-by-line
    proc = subprocess.Popen(
        ["bash", "-c", cmd],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        text=True,
        bufsize=1  # Line buffered
    )

    def checker(candidate: str) -> bool:
        # Send data down the pipe
        proc.stdin.write(f"{candidate}\n")
        proc.stdin.flush()
        
        # Read the response back
        response = proc.stdout.readline().strip()
        return "Success" in response
    
    @atexit.register
    def cleanup():
        proc.stdin.close()
        proc.wait()

    return checker

def make_py_avdu_aegis_checker(file: str, **kwargs):
    from py_avdu.encrypted_classes import VaultEncrypted

    vault_dict = json.loads(pathlib.Path(file).read_text())

    encrypted = VaultEncrypted(**vault_dict)

    def checker(candidate: str) -> bool:
        try:
            encrypted.find_master_key(candidate)
            return True
        except ValueError:
            return False
        

    return checker


def test_passwords_sequentially(
    candidates: Iterable[str],
    test_func: Callable[[str], bool],
    verbosity: int = 0,
    update_every: int | None = None,
    total: int | None = None,
    print_passwords: bool = False,
    **kwargs,
) -> tuple[str, int] | None:
    
    out_of_total = "" if total is None else f"/{total}"

    if update_every is None:
        update_every = max(1, total // 300)
    if verbosity >= 1:
        update_every = min(update_every, 1000)

    for i, candidate in enumerate(candidates, start=1):
        if test_func(candidate):
            return candidate, i

        if i % update_every:
            continue
        if verbosity == 0:
            print_to_stderr(".", end="", flush=True)
        elif verbosity >= 2 and print_passwords:
            print_to_stderr(f"{i}{out_of_total}) tried: {candidate}", flush=True)
        else:
            print_to_stderr(f"{i}{out_of_total}", flush=True)

    return None


default_password_protected_file_checker_factories = {
    ".7z" : make_7zip_checker,
}


def default_checker_factory(*args: str, **kwargs):
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
    password_guess: str | None = None,
    max_subs: int = 2,
    checker_factory: Callable[[str], Callable[[str], bool]] = make_subprocess_checker,
    extract_to: str | None = None,
    password_generator: Callable[[str, int], tuple[int | None, Iterator[str]]] = candidate_passwords_from_alt_chars,
    alt_char_map: dict[str, list[str]] = SHIFT_AND_LEET_BI_MAP,
    **kwargs,
) -> tuple[str, int] | None:

    checker = checker_factory(*extras, extract_to=extract_to)
    if password_guess is None:
        password_guess = getpass.getpass("Input password guess: ")
    total, candidates = password_generator(guess=password_guess, max_subs=max_subs, alt_char_map=alt_char_map)
    return test_passwords_sequentially(candidates, checker, total=total, **kwargs)



parser = argparse.ArgumentParser()
parser.suggest_on_error = True
parser.add_argument(
    "--max-subs",
    '-N',
    type=int,
    default=2,
    help=("The maximum number of character substitutions "
          "that will be applied to the guess"
    ),
)
parser.add_argument('--verbosity', '-v', action='count', default=0)
parser.add_argument(
    '--output-file',
    '-o',
    type=str,
    default="",
    help="File to write found passwords to.",
)
parser.add_argument(
    '--print-passwords',
    '-P',
    action="store_true",
    help=("Set this option to print passwords to stderr. "
          "By default, neither found passwords (nor candidates if -vv) are printed. "
          "E.g. if extracting a password-protected archive as a side-effect is sufficient "
          "(and you intend to re-encrypt it with a different password anyway)."
    ),
)
parser.add_argument("--password-guess", "-p", default=None, help=(
    "WARNING! If given on the command line, its value may be saved by your shell "
    "and e.g. appear in the Bash history file.  Otherwise, you will be prompted to "
    " securely enter this before the search can begin. "
    )
)
parser.add_argument(
    "--extract-to",
    "-x",
    default=None,
    help=("The dir to try to extract archives in "
          "(if using an external program as the password checker)"
         ),
)  
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
    alt_char_map=SHIFT_AND_LEET_BI_MAP,
)

def add_mutex_group(
    title: str | None = None,
    description: str | None = None,
    required: bool = False,
    ):
    arg_group = parser.add_argument_group(title=title, description=description)
    mutex_arg_group = arg_group.add_mutually_exclusive_group(required=required)
    return mutex_arg_group

checker_factories_group = add_mutex_group(
    "Password checker",
    "The method (if any) used to test candidate passwords."
)

def add_checker_factory_arg(name, checker_factory, help: str | None = None):
    checker_factories_group.add_argument(
        name,
        dest="checker_factory",
        action="store_const",
        const=checker_factory,
        help=help,
    )
add_checker_factory_arg("--7zip", make_7zip_checker)
add_checker_factory_arg("--7zip-persistent", make_persistent_7zip_checker)
add_checker_factory_arg("--shell", make_subprocess_checker)
add_checker_factory_arg("--py7zr", make_py7zr_checker)
add_checker_factory_arg("--aegis-pyavdu", make_py_avdu_aegis_checker)
add_checker_factory_arg(
    "--pipe",
    make_password_candidate_piper,
    help=("Print all password candidates to stdout, "
          "e.g. to pipe them to an external password checking program. "
          "Overrides --print-passwords. "     
    ),
)

alt_char_map_group = add_mutex_group(
    "Character map",
    ("The mapping for alternative characters, "
    "to be used to generate candidate passwords from. "
    )
)

def add_alt_char_map_arg(name, alt_char_map, help: str | None = None):
    alt_char_map_group.add_argument(
        name,
        dest="alt_char_map",
        action="store_const",
        const=alt_char_map,
        help=help,
    )
add_alt_char_map_arg("--shift_and_leet", SHIFT_AND_LEET_BI_MAP) 




def cli(args: list[str] = sys.argv[1:]) -> int:

    if not args:
        parser.print_help()
        return 0

    namespace = parser.parse_args()

    if namespace.password_guess is not None:
        warnings.warn(
            "Password guess given on command line may be stored in history. "
            "After this program ends, you may wish to delete the latest entry, "
            "e.g. by running: history -d $(history 1 | awk '{print $1}')"
        )
    
    kwargs = vars(namespace).copy()

    output_file = kwargs.pop("output_file")

    t0 = time.time()

    result = try_find_password_sequentially(**kwargs)

    t1 = time.time()

    if result is None:
        print_to_stderr(f"\n\nCould not find password. Try a different guess, or increasing max substitutions (-N) ? ")
        return 1


    password, i = result
    msg = f"\n Found password (guess number: {i}) in {t1-t0:.3f} seconds"
    print_to_stderr(msg, end="")

    print_to_stderr(f" {password=}" if namespace.print_passwords else "")

    if output_file:
        with open(output_file, "at") as f:
            f.write(f"{msg}, {password=}")
    return 0

if __name__ == '__main__':
    cli()