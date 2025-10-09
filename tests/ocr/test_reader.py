import itertools
from pathlib import Path
from unittest import mock
from unittest.mock import Mock

import pytest
from PIL import Image
from pytesseract import TesseractError

from hope_documents.exceptions import ExtractionError
from hope_documents.ocr.loaders import (
    BWLoader,
    CV2Loader,
    EnhancedLoader,
    ImprovedLoader,
    Loader,
    PILLoader,
    SmartLoader,
)
from hope_documents.ocr.reader import Reader

images_dir = Path(__file__).parent.parent / "images"

valid_images = [p for p in images_dir.rglob("_valid/*") if not p.is_dir() and not p.name.startswith("_")]
invalid_images = [p for p in images_dir.rglob("_invalid/*") if not p.is_dir() and p.name.startswith("_")]
loaders = [BWLoader, CV2Loader, PILLoader, SmartLoader, EnhancedLoader, ImprovedLoader]

args = list(itertools.product(valid_images, loaders))


def make_id(entry: tuple[type[Loader], Path]) -> str:
    return f"{entry[0].relative_to(images_dir)} - {entry[1].__name__}"


@pytest.fixture(params=args, ids=[make_id(p) for p in args])
def image(request) -> Image.Image:
    loader = request.param[1]()
    return loader.load(request.param[0])


@pytest.fixture
def reader(request):
    return Reader(getattr(request, "param", ""))


@pytest.mark.parametrize("reader", ["--oem 3 --psm 11"], indirect=True)
def test_reader_valid(reader: Reader, image):
    text = reader.extract(image)
    assert text


def test_reader_error(reader: Reader):
    with mock.patch("pytesseract.image_to_string") as m:
        m.side_effect = TesseractError("", "")
        with pytest.raises(ExtractionError):
            reader.extract(Mock())
