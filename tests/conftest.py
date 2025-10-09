import logging
import os
import sys
from pathlib import Path

import pytest
import responses

here = Path(__file__).parent
sys.path.insert(0, str(here / "../src"))
sys.path.insert(0, str(here / "_demoapp"))
sys.path.insert(0, str(here / "_extras"))


def pytest_configure(config):
    os.environ["DJANGO_SETTINGS_MODULE"] = "hope_live.config.settings"
    for silenced in ["faker", "PIL", "matplotlib", "pytesseract"]:
        logger = logging.getLogger(silenced)
        logger.handlers.clear()
        logger.setLevel(logging.CRITICAL)


@pytest.fixture
def mocked_responses():
    with responses.RequestsMock(assert_all_requests_are_fired=False) as rsps:
        yield rsps
