import subprocess

command = """\
veracrypt --text --non-interactive --create --encryption=AES --hash=SHA-512 --pim=0 --volume-type=normal --filesystem=FAT --keyfiles="" --size=512K --password=test test.hc
"""

subprocess.run(
    command,
    check=True,
    capture_output=True,
    shell=True,
)
