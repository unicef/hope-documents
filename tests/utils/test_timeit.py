import time

import pytest

from hope_documents.utils.timeit import format_elapsed_time, time_it


@pytest.mark.parametrize(
    ("seconds", "expected_str"),
    [
        (0, "00:00:00:000"),
        (0.123, "00:00:00:123"),
        (1, "00:00:01:000"),
        (59.999, "00:00:59:999"),
        (60, "00:01:00:000"),
        (61.5, "00:01:01:500"),
        (3600, "01:00:00:000"),
        (3661.101, "01:01:01:101"),
    ],
)
def test_format_elapsed_time(seconds, expected_str):
    """Test that format_elapsed_time correctly formats durations."""
    assert format_elapsed_time(seconds) == expected_str


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
