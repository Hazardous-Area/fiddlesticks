import os
from pathlib import Path
import queue
import sys
from collections.abc import Callable, Iterable
from multiprocessing import Event, Process, Queue
from multiprocessing.synchronize import Event as EventT

from fiddlesticks import (
    candidate_passwords_from_alt_chars,
    make_MS_Office_files_key_checker,
)

type GuessInfo = tuple[int, tuple[str, int]]


class UnknownCPUCount(Exception):
    pass


def get_cpu_count() -> int:
    cpu_count = (
        os.process_cpu_count() if sys.version_info >= (3, 13) else os.cpu_count()
    )
    if cpu_count is None:
        raise UnknownCPUCount(
            f"Could not find number of CPU cores to run on, {cpu_count=}"
        )
    return cpu_count


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
    num_cores: int | None = None,
    min_queue_size=1_000,
    max_queue_size=10_000,
):

    guesses = iter(guesses)
    pw_found = Event()
    queued_guesses = Queue[GuessInfo](maxsize=max_queue_size)
    incorrect_guess_indices = Queue[int](maxsize=max_queue_size)

    if num_cores is None:
        num_cores = get_cpu_count()
    print(f"Using {num_cores=}")

    workers = [
        Process(
            target=make_worker(
                pw_found, queued_guesses, incorrect_guess_indices, checker
            ),
            args=(),
        )
        for _ in range(num_cores - 1)
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


def main():
    xlsx_file = Path(__file__).parent.parent / "tests" / "data_files" / "test.xlsx"
    checker = make_MS_Office_files_key_checker(XLSX_FILE)
    first_index = 0
    total, guesses = candidate_passwords_from_alt_chars(
        guesses=["te57"],
        first_index=first_index,
    )
    print(f"{total=}")

    parent(
        checker=checker,
        guesses=enumerate(guesses, start=first_index),
    )


if __name__ == "__main__":
    main()
