import queue
from collections.abc import Callable, Iterable
from multiprocessing import Event, Process, Queue
from multiprocessing.synchronize import Event as EventT

type GuessInfo = tuple[int, tuple[str, int]]


def _make_worker_loop_body(
    pw_found: EventT,
    guesses: Queue[GuessInfo],
    incorrect_guess_indices: Queue[int],
    checker: Callable[[str], bool],
):
    def work():
        if pw_found.is_set():
            return False

        try:
            guess_info = guesses.get(timeout=10)
        except queue.Empty:
            return False

        index, (guess, _num_subs) = guess_info

        if checker(guess):
            pw_found.set()
            return False

        incorrect_guess_indices.put(index)
        return True

    return work()


def make_worker(
    pw_found: EventT,
    queued_guesses: Queue[GuessInfo],
    incorrect_guess_indices: Queue[int],
    checker: Callable[[str], bool],
):

    work = _make_worker_loop_body(
        pw_found, queued_guesses, incorrect_guess_indices, checker
    )

    def worker():
        while work():
            pass

    return worker


def report(incorrect_guesses: list[int]):
    pass


def parent(
    checker: Callable[[str], bool],
    guesses: Iterable[GuessInfo],
    N: int = 0,
    initial_guess_index: int = 0,
    min_queue_size=1_000,
    max_queue_size=10_000,
):

    guesses = iter(guesses)
    pw_found = Event()
    queued_guesses = Queue[GuessInfo](maxsize=max_queue_size)
    incorrect_guess_indices = Queue[int](maxsize=max_queue_size)
    N = 16

    workers = [
        Process(
            target=make_worker(
                pw_found, queued_guesses, incorrect_guess_indices, checker
            ),
            args=(),
        )
        for _ in range(N)
    ]
    parent_work = _make_worker_loop_body(
        pw_found, queued_guesses, incorrect_guess_indices, checker
    )

    unqueued_candidates = True

    for worker in workers:
        worker.start()

    while not pw_found.is_set():
        approx_queue_size = queued_guesses.qsize()
        if unqueued_candidates and approx_queue_size <= min_queue_size:
            # Or while workers not timed out
            guess_info = next(guesses, None)
            if guess_info is None:
                unqueued_candidates = False
            else:
                queued_guesses.put(guess_info)
                continue

        indices: list[int] = []
        while True:
            try:
                index = incorrect_guess_indices.get_nowait()
            except queue.Empty:
                break
            indices.append(index)

        report(indices)

        more_work = parent_work()
        if not more_work:
            break
