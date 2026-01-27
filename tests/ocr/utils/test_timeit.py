import time

import pytest

from hope_ocr.utils._timeit import format_elapsed_time, time_it


@pytest.mark.parametrize(
    ("seconds", "hours", "expected_str"),
    [
        (0, True, "00:00:00:000"),
        (0.123, True, "00:00:00:123"),
        (1, True, "00:00:01:000"),
        (59.999, True, "00:00:59:999"),
        (60, True, "00:01:00:000"),
        (61.5, True, "00:01:01:500"),
        (3600, True, "01:00:00:000"),
        (3661.101, True, "01:01:01:101"),
        (3661.101, False, "01:01:101"),
    ],
)
def test_format_elapsed_time(seconds, hours, expected_str):
    """Test that format_elapsed_time correctly formats durations."""
    assert format_elapsed_time(seconds, hours) == expected_str


def test_time_it_context_manager():
    """Test that the time_it context manager measures time correctly."""
    sleep_duration = 0.5

    with time_it() as timer:
        time.sleep(sleep_duration)

    # Check that elapsed time is recorded and is plausible
    assert timer.elapsed < sleep_duration * 2  # Should be reasonably close

    # Check that the human-readable format is generated
    assert timer.human == format_elapsed_time(timer.elapsed)
    assert timer.human.startswith("00:00:00:")
