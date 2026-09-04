import subprocess

# command = veracrypt --text --password="test" --non-interactive --keyfiles="" --pim=0 --protect-hidden=no --mount test.hc /mnt/vc
commands = [
"/usr/bin/veracrypt",
"--text",
"--password=test",
"--non-interactive",
"--keyfiles=",
"--pim=0",
"--protect-hidden=no",
"--mount",
"/root/test.hc",
"/mnt/vc",
]

subprocess.run(commands)
