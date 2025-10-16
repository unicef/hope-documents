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


@pytest.fixture(autouse=True)
def config_logging(caplog):
    caplog.set_level(logging.CRITICAL, logger="hope_documents")


@pytest.fixture
def mocked_responses():
    with responses.RequestsMock(assert_all_requests_are_fired=False) as rsps:
        yield rsps


@pytest.fixture
def test_dir():
    return Path(__file__).parent


@pytest.fixture
def images_dir(test_dir):
    return test_dir / "images"


def pytest_addoption(parser):
    parser.addoption("--with-report", action="store_true", default=False, help="run tests marked with 'report'")


def pytest_collection_modifyitems(config, items):
    if not config.getoption("--with-report"):
        # --with-report given in cli: do not skip slow tests
        skip_report = pytest.mark.skip(reason="need --with-report option to run")
        for item in items:
            if "report" in item.keywords:
                item.add_marker(skip_report)
