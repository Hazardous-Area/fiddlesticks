from collections import defaultdict
from itertools import islice, product
import math
from multiprocessing import Event, Queue
import queue
from typing import NamedTuple, Callable, Self, Iterator


from fiddlesticks import (
    SHIFT_AND_LEET_BI_MAP,
    _calculate_sub_totals,
    _make_guesses_alt_chars,
    _candidate_from_selected_alts,
)

# Num subs
# Guess number
# -- Compute indices with alts under given map--
# Indices combo number
# -- Compute list of alts --
# Alts product number


def indexable_candidate_passwords_from_alt_chars(
    guesses: list[str],
    starting_index: int = 0,
    min_subs: int = 0,
    max_subs: int = 2,
    alt_char_map: defaultdict[str, list[str]] = SHIFT_AND_LEET_BI_MAP,
) -> tuple[int, Iterator[tuple[int, tuple[str, int]]]]:
    

    guesses_alts = _make_guesses_alt_chars(guesses, alt_char_map)
    sub_totals = _calculate_sub_totals(guesses_alts, min_subs, max_subs)

    sub_total = next_sub_total = 0
    for num_subs, guesses_sub_totals in sub_totals.items():
        next_sub_total += sum(guesses_sub_totals.values())
        if starting_index < next_sub_total:
            break
        sub_total = next_sub_total
    else:
        assert starting_index >= sub_total, f"Loop did not break, but {starting_index=}, {sub_total=}"
        raise ValueError(f"Index too large: {starting_index=} for total candidates: {sub_total}")

    sorted_iterator_lengths = sorted((n, i) for i, n in enumerate(guesses_sub_totals.values()))

    # Add items yielded by Round Robin, allowing for removal of exhausted iterators
    while sorted_iterator_lengths:
        smallest_iterator_length = sorted_iterator_lengths[0][0]
        num_items_until_smallest_iterators_exhausted = smallest_iterator_length * len(sorted_iterator_lengths)
        if starting_index < sub_total + num_items_until_smallest_iterators_exhausted:
            break
        while sorted_iterator_lengths and sorted_iterator_lengths[0][0] == smallest_iterator_length:
            sorted_iterator_lengths.pop(0)

    index_this_cycle = starting_index - sub_total
    index_into_iterator, remaining_iterator_index = divmod(index_this_cycle, len(sorted_iterator_lengths))

    remaining_iterators = sorted(sorted_iterator_lengths, key = lambda t: t[1])
    guess_index = remaining_iterators[remaining_iterator_index][1]
    # Could just use guesses, but in case something changes, that messes with the order
    guess = list(guesses_sub_totals)[guess_index]
    alts = guesses_alts[guess]

    for positions_and_alts in _all_positions_and_alts(num_subs, alts):
        num_candidates_this_combo = math.prod(len(alts) for alts in positions_and_alts.values())
        if starting_index < sub_total + num_candidates_this_combo:
            break
        sub_total += num_candidates_this_combo
    
    for selected in islice(product(*positions_and_alts.values()), starting_index-sub_total, num_candidates_this_combo):
        yield _candidate_from_selected_alts(guess, selected, positions_and_alts), num_subs





    


class GuessData(NamedTuple):
    guesses: list[str]
    num_subs: int
    num_guesses_left: int
    guess_index: int
    guess_char_indices_combo: list[int]
    char_alts_indices: list[int]  # from product

    def to_string() -> str:
        raise NotImplemented
        return ""

    @classmethod
    def from_index(cls, i: int) -> Self:
        raise NotImplemented
        return cls()


def _make_worker_loop_body(
    pw_found: Event,
    guess_indices: Queue[int],
    failed_indices: Queue[int],
    checker: Callable[[str], bool],
):
    def work():
        if pw_found.is_set():
            return False

        try:
            guess_index = guesses.get(timeout=10)
        except queue.Empty:
            return False

        guess = GuessData.from_index(guess_index).form_string()
        if checker(guess.form_string()):
            pw_found.set()
            return False

        failed_indices.put(guess_index)
        return True

    return work()


def make_worker(
    pw_found: Event,
    guess_indices: Queue[int],
    failed_indices: Queue[int],
    checker: Callable[[str], bool],
):

    work = _make_worker_loop_body(pw_found, guess_indices, failed_indices, checker)

    def worker():
        while work():
            pass

    return worker


def parent(
    checker: Callable[[str], bool],
    guess_indices_it,
    N: int = 0,
    initial_guess_index: int = 0,
    min_queue_size=1_000,
    max_queue_size=10_000,
):

    pw_found = Event()
    guess_indices = Queue[int](maxsize=max_queue_size)
    failed_indices = Queue[int](maxsize=max_queue_size)
    N = 16

    workers = [
        make_worker(pw_found, guesses, failed_indices, checker) for _ in range(N)
    ]
    parent_work = _make_worker_loop_body(pw_found, guesses, failed_indices, checker)

    unqueued_candidates = True

    while not pw_found.is_set():
        approx_queue_size = guess_indices.qsize()
        if unqueued_candidates and approx_queue_size <= min_queue_size:
            # Or while workers not timed out
            index = next(guess_indices_it, None)
            if index is None:
                unqueued_candidates = False
            else:
                guess_indices.put(index)
                continue

        newly_failed_indices = []
        while True:
            try:
                newly_failed_indices.append(failed_indices.get_nowait())
            except queue.Empty:
                break
        report(newly_failed_indices)

        more_work = parent_work()
        if not more_work:
            break
