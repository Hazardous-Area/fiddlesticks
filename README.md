# Fiddlesticks!
*"Aaaagh!  I forgot my 7zip password"* - James (more times than he cares to remember).

## Description
Brute force attacks on password encryption, using common variations (e.g. typos and substitusions)
of a small number of guessed passwords.  

 - Attackers targetting a truly random password, must try 2 to the power of the number of bits
 candidate passwords (for each bit length being considered).  
 - Someone using open source password cracking tools, might only need to test every candidate
 password that's similar enough to their best guess of what the password was (and need only consider 
 every candidate within some maximum Weighted-Levenshtein distance from the guess).
 - If Fiddlesticks can crack an archive's password with a starting guess of an empty string, 
 anyone with the archive can also do so - the password wasn't strong enough.
 - If Fiddlesticks fails to crack an archive's password given some starting guess, a lower
 bound on how similar the actual password is to the starting guess can still be deduced
 (e.g. this could be a gentle hint that the starting guess was wrong).
 - Any similar 3rd party password cracking service based on 'best guess' passwords, requires 
 the user to share the guesses for their passwords with the service.  Even if the password
 was not used for anything else, sharing even guesses for secret credentials with 3rd parties, 
 is a critical security issue.
 - Fiddlesticks is designed to minimise the need for this.  It is designed to:
   - a) require as few dependencies as possible,
   - b) require as little code as possible, and
   - c) be as easy to install as possible.  
 The intention if firstly c) assists users to run Fiddlesticks in their own secure
 environment, without requiring them to take their password guesses outside of that.  Secondly
 a) and b) help them decide for themselves whether or not to trust Fiddlesticks 
 in the first place, in particular whether or not it will take their password guesses outside
 of its running environment.
 - A small heirarchy of optional extras, more powerful password cracking tools is 
 available (py7zr and hashcat).
 - But if the user successfully recovers their password via simpler means before, then reviewing,
 auditting, trusting, and installing all that extra code can be avoided entirely.  Hence they are not 
 installed by default.
 - Please do not send us 7zip files containing sensitive data, or encrypted with your real 
 passwords.  Bug reports should use reproducible dummy data and dummy passwords. 
 - Fiddlesticks cannot recover passwords for online accounts.  Online password entry attempts 
 should be rate limited.  Cracking is only possible locally if the website owner shares the 
 password hash with the user, in which case they can probably provide the rest of their 
 account data too (unless users' data is encrypted with keys derived from their 
 passwords but not from the password's hashes).  This would be a highly unusual server.  For 
 starters, password resets are then either impossible, or result in data loss.)

## WARNING!!