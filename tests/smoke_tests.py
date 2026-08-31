from fiddlesticks import candidate_passwords_from_alt_chars


def smoke_test():
    _total, candidates = candidate_passwords_from_alt_chars(
        ["password123"],
        max_subs=2,
    )
    guesses = {candidate for candidate, _num_subs in candidates}
    assert "password12£" in guesses
