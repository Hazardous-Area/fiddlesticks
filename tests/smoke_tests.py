from fiddlesticks import candidate_passwords_from_alt_chars as candidates
    
def smoke_test():
    guesses = set(candidates("password123", max_subs=2))
    assert 'password12£' in guesses