import os
import queue
import sys
from collections.abc import Iterable
from multiprocessing import Process, Queue
from pathlib import Path

from fiddlesticks import (
    Checker,
    MS_OfficeFilesKeyChecker,
    candidate_passwords_from_alt_chars,
    save_ruled_out_indices_to_progress_file,
)

type IndexedGuessInfo = tuple[int, tuple[str, int]]


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
        found_passwords: Queue[IndexedGuessInfo],
        guesses: Queue[IndexedGuessInfo],
        incorrect_guess_indices: Queue[int],
        checker_factory: type[Checker],
        file: Path,
    ):
        self.found_passwords = found_passwords
        self.guesses = guesses
        self.incorrect_guess_indices = incorrect_guess_indices
        self.checker = checker_factory(file=file)

    def __call__(self):
        with self.checker:
            while self.get_and_check_next_guess():
                pass

    def get_and_check_next_guess(self) -> bool:

        if not self.found_passwords.empty():
            return False

        try:
            guess_info = self.guesses.get(timeout=10)
        except queue.Empty:
            return False

        index, (guess, _num_subs) = guess_info

        if self.checker(guess):
            self.found_passwords.put(guess_info)

            return False

        self.incorrect_guess_indices.put(index)
        return True


def parent(
    checker_factory: type[Checker],
    file: Path,
    guesses: Iterable[IndexedGuessInfo],
    num_cores: int | None = None,
    min_queue_size=1_000,
    max_queue_size=10_000,
):

    guesses = iter(guesses)
    queued_guesses: Queue[IndexedGuessInfo] = Queue(maxsize=max_queue_size)
    incorrect_guess_indices: Queue[int] = Queue(maxsize=max_queue_size)
    found_passwords: Queue[IndexedGuessInfo] = Queue(maxsize=1)

    if num_cores is None:
        num_cores = get_cpu_count()
    print(f"Using {num_cores=}")

    workers = [
        Process(
            target=Worker(
                found_passwords,
                queued_guesses,
                incorrect_guess_indices,
                checker_factory,
                file,
            ),
            args=(),
        )
        for _ in range(num_cores - 1)
    ]
    parent_worker = Worker(
        found_passwords, queued_guesses, incorrect_guess_indices, checker_factory, file
    )

    unqueued_candidates = True

    for worker in workers:
        worker.start()

    with parent_worker.checker:
        while found_passwords.empty():
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

            more_work = parent_worker.get_and_check_next_guess()
            if not more_work:
                break

    try:
        return found_passwords.get_nowait()
    except queue.Empty:
        return None


def main():
    xlsx_file = Path(__file__).parent.parent / "tests" / "data_files" / "test.xlsx"
    first_index = 0
    total, guesses = candidate_passwords_from_alt_chars(
        guesses=["te57"],
        first_index=first_index,
    )
    print(f"{total=}")

    parent(
        checker_factory=MS_OfficeFilesKeyChecker,
        file=xlsx_file,
        guesses=guesses,
    )


if __name__ == "__main__":
    main()
