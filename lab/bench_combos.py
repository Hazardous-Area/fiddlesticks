"""  Prove more-itertools.nth_combiantion has negligble impact on performance
Verifying iterators are the same (guess='correcthorsebatterystaple', k=7)
Timing
it.comb / s:         33.004907188999994
mit.nth_comb / s:    40.18167461500002
"""
from collections import deque

import itertools
import math
import timeit
from typing import Iterator

import more_itertools as mit

import fiddlesticks

def f(iterables):
    d = deque(maxlen=100)
    def g():
        for iterable in iterables:
            d.extend(iterable)
    return g


guess = "correcthorsebatterystaple"
alts = [list(fiddlesticks.SHIFT_AND_LEET_BI_MAP[c]) for c in guess]
N = len(guess)
# k = 3  
# k = 5
# k=7
k=9
# k = 15 
# k = N // 2


def _candidates_from_num_subs_and_positions(
    guess: str,
    num_subs: int,
    positions: tuple[int],
    alts: list[list[str]],
) -> Iterator[tuple[str, int]]:
    alts_at_positions = [alts[i] for i in positions if alts[i]]

    if len(alts_at_positions) != num_subs:
        return

    for selected in itertools.product(*alts_at_positions):
        candidate_password = list(guess)
        for i, replacement in zip(positions, selected):
            candidate_password[i] = replacement
        yield "".join(candidate_password), num_subs

def a(guess, k):
    N = len(guess)
    return (
        _candidates_from_num_subs_and_positions(guess, k, combo, alts)
        for combo in itertools.combinations(range(N),k)
    )

def b(guess, k):
    N = len(guess)
    M = math.comb(N, k)
    return (
        _candidates_from_num_subs_and_positions(guess, k, mit.nth_combination(range(N), k, i), alts)
        for i in range(M)
    )

# print(f"Verifying iterators are the same ({guess=}, {k=})")

# for xs, ys in zip(a(guess, k), b(guess, k)):
#     for x, y in zip(xs, ys):
#         assert x == y

print("Timing")
t_a = timeit.timeit(f(a(guess,k)), number=1)
print("it.comb / s:        ", t_a)
t_b = timeit.timeit(f(b(guess,k)), number=1)
print("mit.nth_comb / s:   ", t_b)