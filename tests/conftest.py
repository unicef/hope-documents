import logging
import sys
from pathlib import Path

import pytest
import responses

here = Path(__file__).parent
sys.path.insert(0, str(here / "../src"))
sys.path.insert(0, str(here / "_demoapp"))
sys.path.insert(0, str(here / "_extras"))


def pytest_configure(config):
    for silenced in ["faker", "PIL", "matplotlib", "pytesseract", "factory"]:
        logger = logging.getLogger(silenced)
        logger.handlers.clear()
        logger.setLevel(logging.CRITICAL)


@pytest.fixture
def mocked_responses():
    with responses.RequestsMock(assert_all_requests_are_fired=False) as rsps:
        yield rsps
