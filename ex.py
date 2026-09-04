# Ubuntu 26 & Bash
# wget https://github.com/veracrypt/VeraCrypt/releases/download/VeraCrypt_1.26.29/veracrypt-console-1.26.29-Ubuntu-26.04-amd64.deb
# TODO: verify download
# sudo apt install ./veracrypt-console-1.26.29-Ubuntu-26.04-amd64.deb
#
# veracrypt --text --non-interactive --create --encryption=AES --hash=SHA-512 --pim=0 
# --volume-type=normal --filesystem=none --keyfiles="" --size=512K --password=test test.hc
#
# mkdir /mnt/vc
# veracrypt --text --password="test4" --non-interactive --keyfiles="" --pim=0 --protect-hidden=no --mount test.hc /mnt/vc
# echo $?
# veracrypt --list

# On success, to unmount:
# veracrypt --unmount


# Windows & cmd.exe
# "c:\Program Files\VeraCrypt\VeraCrypt Format.exe" /create test.hc /size 292K /password test /filesystem FAT /silent /force

# Then to test, the following is needed:
# Example failure:
# >"c:\Program Files\VeraCrypt\VeraCrypt.exe" /volume test.hc /letter X /password testh /quit /silent
# C:\...>cd X:
# The system cannot find the drive specified.
# C:\...>echo %ERRORLEVEL%
# 1

# Example success:
# C:\...>"c:\Program Files\VeraCrypt\VeraCrypt.exe" /volume test.hc /letter X /password test /quit /silent
# C:\...>cd X:
# X:\
# C:\...>echo %ERRORLEVEL%
# 0
