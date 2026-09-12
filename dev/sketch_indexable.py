from collections import defaultdict
from multiprocessing import Event, Queue
import queue
from typing import NamedTuple, Callable, Self, Iterator


from fiddlesticks import SHIFT_AND_LEET_BI_MAP

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
    alt_chars: list[list[list[str]]] | None = None,
    alt_char_map: defaultdict[str, list[str]] = SHIFT_AND_LEET_BI_MAP,
) -> tuple[int, Iterator[tuple[int, tuple[str, int]]]]:
    pass


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
