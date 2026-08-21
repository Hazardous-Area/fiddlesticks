# Fiddlesticks!
*"Aaaagh!  I forgot my 7zip password"* - the author.

## Description
Brute force attacks on password encryption, using common variations (e.g. typos and substitusions)
of the password guesses provided, using an efficient minimum of code for easy auditing.  

 - Attackers targetting a truly random password, must try 2 to the power of the number of bits
 candidate passwords (for each bit length being considered).  
 - Someone using open source password cracking tools, might only need to test every candidate
 password that's similar enough to their best guess of what the password was (and need only consider 
 every candidate within some maximum Weighted-Levenshtein distance from the guess).

## WARNING!
 - Any 3rd party password cracking service based on guessed passwords, requires 
 the user to share their password guesses with the service.  Even if the password to be found
 was not used for anything else, sharing even guesses for secret credentials with 3rd parties, 
 is a critical security issue.
 Fiddlesticks is designed to minimise the need for this.  It is designed to:
   - a) require as few dependencies as possible,
   - b) require as little code as possible, and
   - c) be as easy to install as possible.  
 The intention behind these is to assist users to run Fiddlesticks in their own secure
 environment.  Secondly, to help them decide for themselves whether or not to trust Fiddlesticks 
 in the first place (in particular so they can easily review the code for password exfiltration).
