import os
import subprocess
import sys
from pathlib import Path

IS_WINDOWS = sys.platform == "win32"
volume_path = Path("test.hc").resolve()

mount_point = Path("./mnt/vc")
mount_point.mkdir(parents=True, exist_ok=True)

print(f"{volume_path=}, {volume_path.is_file()=}")
print(f"{mount_point=}, {mount_point.is_dir()=}")

# command = veracrypt --text --password="test" --non-interactive --keyfiles="" --pim=0 --protect-hidden=no --mount test.hc /mnt/vc
commands = [
    "/usr/bin/veracrypt",
    "--text",
    "--password=test",
    "--non-interactive",
    '--keyfiles=""',
    "--pim=0",
    "--protect-hidden=no",
    "--mount",
    volume_path.as_posix(),
    mount_point.as_posix(),
]

# result = subprocess.run(" ".join(commands), check=False, capture_output=True, shell=True)

# print(f"{vars(result)=}")

# result.check_returncode()


def make_Veracrypt_checker(file: os.PathLike, **kwargs):

    path = Path(file).resolve()
    assert path.is_file()

    # Ensure we can run Veracrypt in a subprocess.
    subprocess.run(["veracrypt", "--help"], capture_output=True, check=True)

    mount_point = _make_new_tmp_sub_dir(
        tmp_dir=Path("./mnt"),
        name="veracrypt_volume",
    )

    args = [
        "veracrypt",
        "--text",
        "--non-interactive",
        "--keyfiles=",
        "--pim=0",
        "--protect-hidden=no",
        "--mount",
        path.as_posix(),
        f"{mount_point}",
        "--password=",
    ]

    return make_subprocess_checker(*args)


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


checker = make_Veracrypt_checker(volume_path)

assert checker("test")
