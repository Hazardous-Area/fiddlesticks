# Fiddlesticks!
*"Aaaagh!  I forgot my 7zip password"* - James (more times than he cares to remember).
![Tests passing](https://github.com/Hazardous-Area/fiddlesticks/actions/workflows/tests.yml/badge.svg)
![Code qual](https://github.com/Hazardous-Area/fiddlesticks/actions/workflows/lint.yml/badge.svg)

Version 0.2.1.dev

## Description
Password recovery tool, for password-encrypted files, using simple off-line brute 
force attacks.  Password candidates are generated, using common variations 
of a guessed password (e.g. typos and substitutions).  

### Raison d'etre
 - Password-protected file owners recovering their own password themselves, as long as 
they can still recall a rough guess for their password, might only need to test 
every candidate password that's similar enough to the guess.  
 - This may be a much faster and cheaper computation
than the one an adversary must do, without such a guess, but in possession 
of a stolen password protected file[^0].

### Warning
Strictly speaking, Fiddlesticks is a password-protected file recovery tool.  Use it to 
get your files back.  But once you've found a password that protected those files via Fiddlesticks
(or any third party tool) it should not be used again.  Anywhere else it is also used, the 
password should be reset (or the files re-encrypted with a different one).  By default,
Fiddlesticks does not print the password it finds (or any candidates) unless `-P` or `-v` is set 
(or if using `--pipe` with no pipe).

### "Back of envelope" sketch 'calculation'
 - Attackers targetting a truly[^0] random password, must try up to `2**N` 
 candidate passwords (for each bit length `N` being considered). 
 - Specifically, password owners may only need to consider every candidate within some 
 maximum [Weighted-Levenshtein distance](https://en.wikipedia.org/wiki/Edit_distance#Types_of_edit_distance) 
 from their best guess of the forgotten password, lets say a total of `M`.  
 - Fiddlesticks is intended to assist recovering passwords from "close enough" guesses, 
 when `M` is much smaller than `2**N`.
 - If Fiddlesticks can crack an archive's password with a starting guess of an empty string, 
(if `2**N` is also small enough to be feasible, with no guess) then anyone with the 
archive can also do so - the password wasn't strong enough.
 - If Fiddlesticks fails to crack an archive's password given some starting guess, a lower
 bound on how similar the actual password is to the starting guess can still be deduced
 (e.g. this could indicate that the starting guess was wrong).

### Design and security notes
*"FAQ: Why the heck should anyone in their right mind trust this with their password?"*
 - Any similar 3rd party password cracking service based on 'best guess' passwords, requires 
the user to share the guesses for their passwords with the service.  Even if the password
was not used for anything else, sharing even guesses for secret credentials with 3rd parties, 
is a critical security issue.
 - Fiddlesticks is designed to minimise the need for this.  It is designed to i) be as easy 
to install as possible, and in particular ii) require as few dependencies as possible.  
Firstly, the intention of i) is to assist users to run Fiddlesticks in their own secure
environment, locked down as much as they want (e.g. offline and disconnected from 
all external network access), without requiring them to take their 
password guesses outside of that.  For example, for recovery of password encrypted .7z archives,
only a normal installation of 7zip is required on Linux (plus a close enough guess of the password!).
Fiddlesticks can even generate a file of candidate passwords, for external programs, and other 
possible applications.  Secondly, ii) helps users decide for themselves whether or not to trust Fiddlesticks 
in the first place.  In particular whether or not it will take their password guesses outside
of its running environment.  When the project was concieved, the intention was also to 
iii) require as little code as possible.  But the code base has since become somewhat more 
complex, mainly to have a nice CLI.  Simplicity and brevity should both be much 
more highly prized features of software in general.  But you 
be the judge of whether or not c) is still the case.  The application code is all in a single file.

#### General security audit
If considering using any password recovery program at all, perhaps consider the following:
 - does it contain code contained in string literals or obfuscated code?
 - does it utilise arbitrary code execution functions (e.g. `eval`, `exec` and `compile`)?
 - is all the source code visible?
 - does it contain thousands of lines of code?
 - does it require hundreds of third-party dependencies?
 - does it contain compiled binary executables, that are not easily readable?
 - is the code statically typed (so run-time features of dynamic languages are minimised)?
 - is all the code tested?
 - is it tested with high coverage (so all the code really is run, somewhere in the tests)?
 - does it import or install any libraries that allow communication across a network, that
 could be used for exfiltration purposes?
 - does it require root privileges to run?
 - can it be run on any operating system, and in any Docker container?

Full disclaimer:  Fiddlesticks does actually contain 8 lines of Bash in a string 
literal (to avoid the overhead of `subprocess.run` for every single candidate to be 
tested, and to demonstrate how any command line program could read 
password candidates from stdin).  Otherwise we hope the answers to all the other questions
with regards to Fiddlesticks, are all reassuring.

### Usage
```
uvx fiddlesticks
```

For 7z archives, it is possible to simply to automate attempts to open the file via a stock
7zip installed in the system, e.g. from:
```
sudo apt update && sudo apt-get install 7zip
```

Fiddlesticks can also decrypt KeepassXC vaults and Aegis vault files (for TOTP authenticators) if 
[pykeepass](https://pypi.org/project/pykeepass/) and [py-avdu](https://pypi.org/project/py-avdu/) respectively, are 
also installed.

There are a couple of alternative modes too, 

 - firstly: automating any partial external Bash command that a candidate password can be appended to (that obeys the normal return code convention).  Specify `--shell` or by default if the partial command is specified after `--`.

Secondly with `--pipe` candidate passwords can be sent to stdout, from where they can be piped to stdin of a user's own external program or code (all the normal output from fiddlesticks goes to stderr).

Thirdly, if py7zr is also installed, with `--py7zr` fiddlesticks can use it to test passwords for 7z archives,
 entirely within Python.

### Main options
#### Password guesses
If no password is specified, and if a password guess is requires for the selected command,
the user will be prompted to enter their password guesses securely (via Python's `getpass.getpass`).  
For convenience passwords may also be supplied on separate lines of a text file specified 
in `--input-file`, or directly on the command line, each after `--password-guess` or `-p`.  If using
the latter in Bash and similar shells, please be aware the full command entered may be saved 
in the Bash history.  After using Fiddlesticks you should run `history -a` and 
asome `history -d $(history 1 | awk '{print $1}')` command to clear this.

#### Number of substitutions
For candidate password generation strategies that use character substitutions (the only ones supported so far)
the number of substitutions required for each candidate can be capped by setting `--max-subs`

#### Output control & verbosity
If a file is specified in `--output-file` or `-o` Fiddlesticks will write a successfully found 
password to it.  Fiddlesticks does not print any candidate passwords by default (on successfully finding a password, the
candidate number is printed; candidate generation is deterministic), unless:
 - `--print-passwords` or `-P` is set, or
 - `-vv` is set (or `--verbosity --verbosity` or `--verbosity -v`, if you really want to).

### Custom alternative character maps

Any custom JSON file supplied to `--char-map` containing a mapping of characters to alternatives can be used (instead of the default L33t substitutions and capitalisations ascii-based map).  To assist creating this, the default map (or the relevant
sub-mapping applicable for a specified password guess) can be printed to stderr with `--print-char-map` (and `>>`ed 
to a local file, where its JSON can be customised in any text editor).  This provides a simple method for
limiting the substitutions to specific characters in a password guess.

### Other Notes
 - Successful attempts to extract a password-protected archive, result in the archive being
 unencrypted (naturally) by some methods.  Currently all such plaintext unencrypted archives 
 are not deleted from the file system afterwards.  If the options `--extract-to` or `-x` 
 are given, archives are extracted there.
 - Fiddlesticks cannot recover passwords for online accounts.  Online password entry attempts 
 should be rate limited.  Cracking is only possible locally if the website owner shares the 
 password hash with the user, in which case they can probably provide the rest of their 
 account data too.
 - If Fiddlesticks fails to 'crack' or find a known password, this should not be taken as 
 proof of the password's strength.  It won't ever be possible to think everything, and
 we certainly don't wish users to draw a false sense of security from Fiddlesticks.

## Alternatives
 - https://github.com/philsmd/7z2hashcat
 - https://en.wikipedia.org/wiki/Dictionary_attack#Dictionary_attack_software

[^0] Truly random passwords are difficult for humans to remember (without writing them down or saving them).
At the very least, real world adversaries (posessing a stolen file or password hash) are likely to first attempt a [dictionary attack](https://en.wikipedia.org/wiki/Dictionary_attack#Dictionary_attack_software)