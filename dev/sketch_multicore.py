import os
import queue
import sys
from collections.abc import Callable, Iterable
from multiprocessing import Event, Process, Queue
from multiprocessing.synchronize import Event as EventT
from pathlib import Path

from fiddlesticks import (
    MS_OfficeFilesKeyChecker,
    candidate_passwords_from_alt_chars,
    handle_found_password,
    save_ruled_out_indices_to_progress_file,
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


class Worker:
    def __init__(
        self,
        pw_found: EventT,
        guesses: Queue[GuessInfo],
        incorrect_guess_indices: Queue[int],
        checker: Callable[[str], bool],
    ):
        self.pw_found = pw_found
        self.guesses = guesses
        self.incorrect_guess_indices = incorrect_guess_indices
        self.checker = checker

    def __call__(self):
        while self.get_and_check_next_guess():
            pass

    def get_and_check_next_guess(self) -> bool:

        if self.pw_found.is_set():
            return False

        try:
            guess_info = self.guesses.get(timeout=10)
        except queue.Empty:
            return False

        index, (guess, _num_subs) = guess_info

        if self.checker(guess):
            self.pw_found.set()
            handle_found_password(guess, index, print_passwords=True)

            return False

        self.incorrect_guess_indices.put(index)
        return True


def parent(
    checker: Callable[[str], bool],
    guesses: Iterable[GuessInfo],
    num_cores: int | None = None,
    min_queue_size=1_000,
    max_queue_size=10_000,
):

    guesses = iter(guesses)
    pw_found = Event()
    queued_guesses: Queue[GuessInfo] = Queue(maxsize=max_queue_size)
    incorrect_guess_indices: Queue[int] = Queue(maxsize=max_queue_size)

    if num_cores is None:
        num_cores = get_cpu_count()
    print(f"Using {num_cores=}")

    workers = [
        Process(
            target=Worker(pw_found, queued_guesses, incorrect_guess_indices, checker),
            args=(),
        )
        for _ in range(num_cores - 1)
    ]
    parent_worker = Worker(pw_found, queued_guesses, incorrect_guess_indices, checker)

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

        save_ruled_out_indices_to_progress_file(indices)

        more_work = parent_worker()
        if not more_work:
            break

    if pw_found.is_set():
        print("Found password!")


def main():
    xlsx_file = Path(__file__).parent.parent / "tests" / "data_files" / "test.xlsx"
    checker = MS_OfficeFilesKeyChecker(file=xlsx_file)
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
