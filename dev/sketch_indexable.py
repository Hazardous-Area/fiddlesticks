import queue
from collections.abc import Callable
from multiprocessing import Event, Process, Queue
from multiprocessing.synchronize import Event as EventT
from typing import NamedTuple, Self, Iterable



type GuessInfo = tuple[int, tuple[str, int]]

def _make_worker_loop_body(
    pw_found: EventT,
    guesses: Queue[GuessInfo],
    incorrect_guesses: Queue[GuessInfo],
    checker: Callable[[str], bool],
):
    def work():
        if pw_found.is_set():
            return False

        try:
            guess = guesses.get(timeout=10)
        except queue.Empty:
            return False

        if checker(guess):
            pw_found.set()
            return False

        incorrect_guesses.put(guess)
        return True

    return work()


def make_worker(
    pw_found: EventT,
    queued_guesses: Queue[GuessInfo],
    incorrect_guesses: Queue[GuessInfo],
    checker: Callable[[str], bool],
):

    work = _make_worker_loop_body(pw_found, queued_guesses, incorrect_guesses, checker)

    def worker():
        while work():
            pass

    return worker


def report(incorrect_guesses: list[str]):
    pass


def parent(
    checker: Callable[[str], bool],
    guesses: Iterable[GuessInfo],
    N: int = 0,
    initial_guess_index: int = 0,
    min_queue_size=1_000,
    max_queue_size=10_000,
):

    pw_found = Event()
    queued_guesses = Queue[GuessInfo](maxsize=max_queue_size)
    incorrect_guesses = Queue[GuessInfo](maxsize=max_queue_size)
    N = 16

    workers = [
        Process(
            target=make_worker(pw_found, queued_guesses, incorrect_guesses, checker),
            args=(),
        )
        for _ in range(N)
    ]
    parent_work = _make_worker_loop_body(
        pw_found, queued_guesses, incorrect_guesses, checker
    )

    unqueued_candidates = True

    for worker in workers:
        worker.start()

    while not pw_found.is_set():
        approx_queue_size = queued_guesses.qsize()
        if unqueued_candidates and approx_queue_size <= min_queue_size:
            # Or while workers not timed out
            guess_info = next(guesses, None)
            if guess is None:
                unqueued_candidates = False
            else:
                queued_guesses.put(guess_info)
                continue

        newly_incorrect_guesses = []
        while True:
            try:
                newly_incorrect_guesses.append(incorrect_guesses.get_nowait())
            except queue.Empty:
                break
        report(newly_incorrect_guesses)

        more_work = parent_work()
        if not more_work:
            break
