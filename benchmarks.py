import argparse
import os
import time
import tomllib
from collections import deque
from pathlib import Path

import fiddlesticks

metadata = tomllib.loads(Path("pyproject.toml").read_text())
version = metadata["project"]["version"]
# version = fiddlesticks.__version__


# guess = "abcd"
guess = "correcthorsebatterystaple"
num_cpu_cores_available = os.process_cpu_count()


def f(x, guess=guess):
    N, pwds = fiddlesticks.candidate_passwords_from_alt_chars([guess], max_subs=x)
    print(f"{N=} ", end="", flush=True)
    cands = [pwd for pwd, n in pwds]
    print(f"{len(cands)=}")
    return cands


def benchmark_candidate_generation(
    max_num_subs: int = 8,
    iterate: bool = False,
    **kwargs,
):
    queue = deque(maxlen=1000)
    for i in range(min(max_num_subs, len(guess)) + 1):
        N, pwds = fiddlesticks.candidate_passwords_from_alt_chars(
            [guess],
            min_subs=i,
            max_subs=i,
        )
        print(f"num subs: {i:2}, num candidates: {N:10}... ", end="", flush=True)
        if not iterate:
            print()
            continue
        queue.clear()
        t0 = time.time()
        queue.extend(pwds)
        t1 = time.time()
        t = t1 - t0
        print(
            f" ...iterating pwds took: {t:.3f} seconds ({1e6 * t / N:.3f} us per candidate).",
            flush=True,
        )


# benchmark_candidate_generation(iterate=True)
# E.g. (correcthorsebatterystaple):
#
# (.venv) root@ubuntu-4gb-fsn1-1:~/fiddlesticks# python ex.py
# num subs:  0, num candidates:          1...  ...iterating pwds took: 0.000 seconds (44.107 us per candidate).
# num subs:  1, num candidates:         42...  ...iterating pwds took: 0.000 seconds (2.390 us per candidate).
# num subs:  2, num candidates:        842...  ...iterating pwds took: 0.001 seconds (1.510 us per candidate).
# num subs:  3, num candidates:      10724...  ...iterating pwds took: 0.017 seconds (1.550 us per candidate).
# num subs:  4, num candidates:      97431...  ...iterating pwds took: 0.140 seconds (1.442 us per candidate).
# num subs:  5, num candidates:     672118...  ...iterating pwds took: 1.135 seconds (1.689 us per candidate).
# num subs:  6, num candidates:    3658692...  ...iterating pwds took: 5.651 seconds (1.544 us per candidate).
# num subs:  7, num candidates:   16123752...  ...iterating pwds took: 25.895 seconds (1.606 us per candidate).
# num subs:  8, num candidates:   58559439...  ...iterating pwds took: 96.775 seconds (1.653 us per candidate).

#
# num subs:  0, num candidates: 1
# num subs:  1, num candidates: 42
# num subs:  2, num candidates: 842
# num subs:  3, num candidates: 10724
# num subs:  4, num candidates: 97431
# num subs:  5, num candidates: 672118
# num subs:  6, num candidates: 3658692
# num subs:  7, num candidates: 16123752
# num subs:  8, num candidates: 58559439
# num subs:  9, num candidates: 177498966
# num subs: 10, num candidates: 453037050
# num subs: 11, num candidates: 979620036
# num subs: 12, num candidates: 1801443081
# num subs: 13, num candidates: 2822358762
# num subs: 14, num candidates: 3767206488
# num subs: 15, num candidates: 4275886128
# num subs: 16, num candidates: 4111063344
# num subs: 17, num candidates: 3327612384
# num subs: 18, num candidates: 2247342848
# num subs: 19, num candidates: 1250452992
# num subs: 20, num candidates: 563093248
# num subs: 21, num candidates: 200017408
# num subs: 22, num candidates: 53925888
# num subs: 23, num candidates: 10366976
# num subs: 24, num candidates: 1265664
# num subs: 25, num candidates: 73728


# To set up test data files:
# cp fiddlesticks/tests/data_files/* .
# cd fiddlesticks
# python -c 'import tests.helpers as h; h._try_make_veracrypt_volume("../test.hc","test")'
# python -c 'from pathlib import Path; import tests.helpers as h; h._try_make_ssh_key_files(Path(".."))'
# cd ..
# git clone --depth=1 https://github.com/Sammy-T/avdu/
# cp avdu/test/data/aegis_encrypted.json .

# To run:
# python fiddlesticks/benchmarks.py


test_files = [
    ("test.docx", "test.xlsx"),
    "Test_vault_Do_Not_Use.kdbx",
    "aegis_encrypted.json",
    "foo.7z",
    ("openssh-modern.key", "basic_PEM.key", "openssl_PEM.key"),
    "test.hc",
]


files = {
    Path(files[0] if isinstance(files, tuple) else files): 0.1 for files in test_files
}


def benchmark_candidate_testing(
    output_file: Path = Path("fiddlesticks_benchmarks.txt"),
    max_time_s: int = 1000,
    min_num_subs: int = 0,
    max_num_subs: int = 3,
    num_cores: int = 1,
):

    def output(s: str):
        with open(output_file, "at") as f:
            f.write(s)

    msg = f"## Benchmarks\n - fiddlesticks v{version}\n - {guess=}"
    print(msg)
    output(f"{msg}\n\n")

    # Markdown table format
    headers = [f" {file.suffix:5}/s | per pwd/cpu ms |" for file in files]
    headers.insert(0, "| Num subs |")
    headers.insert(1, "Num pwds |")
    for header in headers:
        output(header)

    # Delimiter row
    output(f"\n|{'-' * (len(headers[0]) - 2)}|")
    output(f":{'-' * (len(headers[1]) - 3)}:|")
    output("|".join(f":{'-' * 7}:|:{'-' * 10}:" for header in headers[2:]))
    output("|\n")

    for num_subs in range(min_num_subs, min(max_num_subs, len(guess)) + 1):
        L = len(headers[0])

        output(f"|{num_subs:{L - 3}} |")

        printed_num_pwds = False

        for header, (file, cpu_ms_per_pwd) in zip(headers[2:], files.items()):
            L = len(header)

            # For num_subs = 8, caching all candidates requires 8GB,
            # so make a new iterator for each file
            total, _pwds = fiddlesticks.candidate_passwords_from_alt_chars(
                [guess],
                min_subs=num_subs,
                max_subs=num_subs,
            )

            if not printed_num_pwds:
                output(f" {total:{len(headers[1]) - 3}} |")
                printed_num_pwds = True

            # Skip this one, if it's estimated to take longer than max_time_s
            if (cpu_ms_per_pwd / 1000) * (total / num_cores) >= max_time_s:
                output(f"{' ':9}|{' ':{L - 11}}|")
                continue

            file_name = file.as_posix()
            # checker_factory = fiddlesticks._default_Checker_selector(file_name)
            # updater = fiddlesticks.Updater()

            t0 = time.time()
            fiddlesticks.cli(
                [
                    "--new-search",
                    f"--password-guess={guess}",
                    f"--num-cores={num_cores}",
                    f"--max-subs={num_subs}",
                    f"--min-subs={num_subs}",
                    file_name,
                ]
            )
            t1 = time.time()

            t_s = t1 - t0

            total_cpu_ms = 1000 * t_s * num_cores

            cpu_ms_per_pwd = total_cpu_ms / total
            # Update the current value in the dict, with (hopefully)
            # this better estimate (initialised to zero above).
            files[file] = cpu_ms_per_pwd
            output(f"{int(t_s):9}|{cpu_ms_per_pwd:{L - 11}.3f}|")

        output("\n")


def benchmark_checkers(
    output_file: Path = Path("checker_benchmarks.txt"),
    **kwargs,
):

    def output(s: str):
        with open(output_file, "at") as f:
            f.write(s)

    start = 123
    N = 200
    stop = start + N
    guess_range = range(123, 144)
    msg = f"## Checker benchmarks\n - fiddlesticks v{version}\n - password{start}...{stop - 1}"
    print(msg)
    output(f"{msg}\n\n")

    # Markdown table format
    headers = [f" {file.suffix:5}/s | per pwd/cpu ms |" for file in files]
    headers.insert(0, "|          |")
    headers.insert(1, "Num pwds |")
    for header in headers:
        output(header)

    # Delimiter row
    output(f"\n|{'-' * (len(headers[0]) - 2)}|")
    output(f":{'-' * (len(headers[1]) - 3)}:|")
    output("|".join(f":{'-' * 7}:|:{'-' * 10}:" for header in headers[2:]))
    output("|\n")

    L = len(headers[0])

    output(f"|{' ' * (L - 2)}|")

    total = len(guess_range)

    output(f" {total:{len(headers[1]) - 3}} |")

    for header, (file, _cpu_ms_per_pwd) in zip(headers[2:], files.items()):
        L = len(header)

        t0 = time.time()
        guesses = [f"password{i}" for i in guess_range]
        last_guess = guesses.pop()
        guesses_it = iter(guesses)

        file_name = file.as_posix()
        checker_factory = fiddlesticks._default_Checker_selector(file_name)

        with checker_factory(file=file_name) as checker:
            checker(next(guesses_it))
            _t1 = time.time()

            for guess in guesses_it:
                checker(guess)

            t2 = time.time()

            checker(last_guess)

            t3 = time.time()

        t_inc_overhead_ms = 1000 * (t3 - t0)
        delta_t_per_check_ms = (1000 * (t3 - t2)) / total

        output(f"{int(t_inc_overhead_ms):9}|{delta_t_per_check_ms:{L - 11}.3f}|")

    output("\n")


parser = argparse.ArgumentParser()
parser.add_argument(
    "--output-file", type=Path, default=Path("fiddlesticks_benchmarks.txt")
)
parser.add_argument("--max-num-subs", type=int, default=3)

subparsers = parser.add_subparsers(required=True)


def add_subparser(name: str, func):
    subparser = subparsers.add_parser(name, parents=[parser])
    subparser.set_defaults(func=func)
    return subparser


generator_parser = add_subparser("generator", benchmark_candidate_generation)
end_to_end_parser = add_subparser("end_to_end", benchmark_candidate_testing)
_checker_parser = add_subparser("checker", benchmark_checkers)

generator_parser.add_argument("--iterate", type=bool, default=False)

end_to_end_parser.add_argument("--max-time-s", type=int, default=1000)
end_to_end_parser.add_argument("--min-num-subs", type=int, default=0)
end_to_end_parser.add_argument("--num-cores", type=int, default=1)

if __name__ == "__main__":
    namespace = parser.parse_args()
    # print(
    #     f"Testing: {guess=}  (num_cores = {namespace.num_cores}, {num_cpu_cores_available=}). "
    # )
    # benchmark_candidate_testing(**vars(namespace))
    namespace.func(output_file=namespace.output_file)

# E.g.
# fiddlesticks_benchmarks.txt
# Benchmarking fiddlesticks against guess='correcthorsebatterystaple'
#
# Num subs |Num pwds || .xlsx/s, per pwd/ms | .kdbx/s, per pwd/ms | .json/s, per pwd/ms | .7z/s, per pwd/ms | .key/s, per pwd/ms | .hc/s, per pwd/ms
# ---------------------------------------------------------------------------------------------------------------------------------------------------
#        0         1       0           63.0      0          106.0      0          140.0      0        214.0      0         259.0     44      44102.0
#        1        42       2           52.0      3           89.0      5          140.0      9        219.0     10         261.0
