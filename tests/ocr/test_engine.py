import os
from pathlib import Path
from unittest import mock
from unittest.mock import MagicMock

import pytest

from hope_ocr.ocr.__cli__ import load_expectations
from hope_ocr.ocr.engine import CV2Config, MatchMode, Processor, Scanner, TSConfig
from hope_ocr.utils.image import get_image

images_dirs = [Path(__file__).parent.parent / "images/and/"]

EXPECTATIONS = load_expectations(str(Path(__file__).parent / "expectations.csv"))


def sample_images():
    """Fixture that collects test parameters from the 'data' folder."""
    scanner = Scanner(images_dirs)
    for f in scanner.files:
        yield f


@pytest.fixture(params=[{"psm": 11, "oem": 3, "number_only": False}])
def processor(request) -> Processor:
    ts_config = TSConfig(**request.param)
    cv2_config = CV2Config()
    return Processor(ts_config, cv2_config)


def test_scanner(tmp_path):
    """Test the Scanner class."""
    dir1 = tmp_path / "dir1"
    dir1.mkdir()
    file1 = dir1 / "file1.txt"
    file1.touch()
    sub_dir = dir1 / "subdir"
    sub_dir.mkdir()
    file2 = sub_dir / "file2.txt"
    file2.touch()

    file3 = tmp_path / "file3.txt"
    file3.touch()

    scanner = Scanner(str(dir1), str(file3))
    files = sorted(list(scanner.files))
    assert files == [str(file1), str(file2), str(file3)]


def test_processor_process(processor, tmp_path):
    """Test the Processor.process method."""
    image_path = tmp_path / "image.png"
    image_path.touch()

    processor.reader = MagicMock()
    processor.reader.extract.return_value = "extracted text"

    loader_mock = MagicMock()
    loader_mock.load.return_value = MagicMock()
    processor.loaders = [loader_mock]

    results = list(processor.process(str(image_path)))
    assert len(results) == 1
    assert results[0].text == "extracted text"
    loader_mock.load.assert_called_with(str(image_path))
    processor.reader.extract.assert_called_once()


@pytest.mark.parametrize(
    "mode,expected_len", [(MatchMode.FIRST, 1), (MatchMode.ALL, 2)]
)
def test_find_text_match_modes(processor, mode, expected_len):
    """Test find_text with different MatchModes."""
    image = MagicMock()
    pattern = "test"

    processor.find_single = MagicMock(
        side_effect=[
            ("text1", MagicMock(distance=0.1)),
            ("text2", MagicMock(distance=0.2)),
        ]
    )

    mock_loader = MagicMock()
    mock_loader.rotate.return_value = [(image, 0), (image, 90)]
    processor.loaders = [mock_loader]

    findings = list(processor.find_text(image, pattern, mode=mode, psms=(11,)))
    assert len(findings) == expected_len


def test_find_text_best_mode(processor):
    """Test find_text with MatchMode.BEST."""
    image = MagicMock()
    pattern = "test"

    match1 = MagicMock()
    match1.distance = 0.2
    match2 = MagicMock()
    match2.distance = 0.1

    processor.find_single = MagicMock(side_effect=[("text1", match1), ("text2", match2)])
    mock_loader = MagicMock()
    mock_loader.rotate.return_value = [(image, 0), (image, 90)]
    processor.loaders = [mock_loader]

    findings = list(processor.find_text(image, pattern, mode=MatchMode.BEST, psms=(11,)))
    assert len(findings) == 1
    assert findings[0].match.distance == 0.1


@pytest.mark.parametrize("filename", sample_images())
def test_search_text(processor, filename, test_dir) -> None:
    with mock.patch.object(os, "getcwd", return_value=str(test_dir.parent.absolute())):
        file_label = str(Path(filename).absolute().relative_to(os.getcwd()))
        if expected_args := EXPECTATIONS.get(file_label):
            pattern, found, distance = expected_args
            image = get_image(filename)
            findings = list(
                processor.find_text(image, pattern, mode=MatchMode.FIRST, debug=True)
            )
            if found:
                assert len(findings) == 1
                assert findings[0].found is found
                assert findings[0].match
            else:
                assert not findings
