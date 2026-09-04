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
