import os
from pathlib import Path
from unittest import mock

import pytest

from hope_documents.ocr.__cli__ import load_expectations
from hope_documents.ocr.engine import CV2Config, MatchMode, Processor, TSConfig
from hope_documents.utils.image import get_image

images_dirs = [Path(__file__).parent.parent / "images/and/"]

EXPECTATIONS = load_expectations(str(Path(__file__).parent / "expectations.csv"))


def sample_images():
    """Fixture that collects test parameters from the 'data' folder."""
    from hope_documents.ocr.engine import Scanner

    scanner = Scanner(images_dirs)
    for f in scanner.files:
        yield f


@pytest.fixture(params=[{"psm": 11, "oem": 3, "number_only": False}])
def processor(request) -> Processor:
    ts_config = TSConfig(**request.param)
    cv2_config = CV2Config()
    return Processor(ts_config, cv2_config)


@pytest.mark.parametrize("filename", sample_images())
def test_search_text(processor, filename, test_dir) -> None:
    with mock.patch.object(os, "getcwd", return_value=str(test_dir.parent.absolute())):
        file_label = str(Path(filename).absolute().relative_to(os.getcwd()))
        if expected_args := EXPECTATIONS.get(file_label):
            pattern, found, distance = expected_args
            image = get_image(filename)
            findings = list(processor.find_text(image, pattern, mode=MatchMode.FIRST, debug=True))
            if found:
                assert len(findings) == 1
                assert findings[0].found is found
                assert findings[0].match
            else:
                assert not findings
