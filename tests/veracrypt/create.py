import subprocess
from pathlib import Path

path = Path("test.hc")

command = f'veracrypt --text --non-interactive --create --encryption=AES --hash=SHA-512 --pim=0 --volume-type=normal --filesystem=FAT --keyfiles="" --size=512K --password=test {path.resolve()}'

subprocess.run(
    command,
    check=True,
    capture_output=True,
    shell=True,
)

print(f"{path.resolve()=}, {path.resolve().is_file()}")
