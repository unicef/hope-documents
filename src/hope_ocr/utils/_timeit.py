import time
from collections.abc import Generator
from contextlib import contextmanager

MINUTE = 60
HOUR = MINUTE * 60
DAY = HOUR * 24


class Timer:
    def __init__(self) -> None:
        self.start = time.process_time()
        self.elapsed = 0.0

    def stop(self) -> None:
        self.elapsed = time.process_time() - self.start

    def get_partial(self) -> float:
        return time.process_time() - self.start

    @property
    def human(self) -> str:
        return format_elapsed_time(self.elapsed)


@contextmanager
def time_it() -> Generator[Timer, None, None]:
    ret = Timer()
    try:
        yield ret
    finally:
        ret.stop()


def format_elapsed_time(seconds_float: float, hours: bool = True) -> str:
    """Format a duration in seconds into HH:MM:SS:MS."""
    total_seconds = int(seconds_float)
    milliseconds = int((seconds_float - total_seconds) * 1000)
    minutes, seconds = divmod(total_seconds, 60)
    _hours, _minutes = divmod(minutes, 60)
    if hours:
        return f"{_hours:02d}:{_minutes:02d}:{seconds:02d}:{milliseconds:03d}"
    return f"{_minutes:02d}:{seconds:02d}:{milliseconds:03d}"
