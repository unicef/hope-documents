import logging

import pytest
from colorama import Fore

from hope_documents.utils.logging import LevelFormatter


@pytest.mark.parametrize(
    ("level", "color"),
    [
        (logging.DEBUG, Fore.MAGENTA),
        (logging.INFO, Fore.BLUE),
        (logging.WARN, Fore.YELLOW),
        (logging.ERROR, Fore.RED),
        (logging.CRITICAL, Fore.RED),
        (logging.NOTSET, Fore.LIGHTWHITE_EX),  # Test default color
    ],
)
def test_level_formatter(level, color):
    """Test that LevelFormatter applies the correct color for each log level."""
    formatter = LevelFormatter()
    record = logging.LogRecord(
        name="test_logger",
        level=level,
        pathname="/fake/path",
        lineno=123,
        msg="This is a test message",
        args=(),
        exc_info=None,
    )

    formatted_log = formatter.format(record)

    # Check that the correct color is at the start of the message
    expected_prefix = f"{color}{logging.getLevelName(level)}{Fore.RESET}:"
    assert formatted_log.startswith(expected_prefix)

    # Check that the rest of the message is formatted as expected
    expected_suffix = f" {Fore.LIGHTWHITE_EX}test_logger{Fore.RESET} - This is a test message"
    assert formatted_log.endswith(expected_suffix)
