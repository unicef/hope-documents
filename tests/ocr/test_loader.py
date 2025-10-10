from pathlib import Path

import pytest

from hope_documents.exceptions import InvalidImageError
from hope_documents.ocr.loaders import loader_registry

images_dir = Path(__file__).parent.parent / "images"

valid_images = [p for p in images_dir.rglob("*.png") if not p.is_dir() and not p.name.startswith("_")]
invalid_images = [p for p in images_dir.rglob("*") if not p.is_dir() and p.name.startswith("_")]


@pytest.fixture(params=loader_registry)
def loader(request):
    return request.param(scale_factor=0.9)


# @pytest.mark.parametrize("loader", [PILLoader, CV2Loader, SmartLoader, BWLoader], indirect=True)
@pytest.mark.parametrize("img", valid_images, ids=[str(p.relative_to(images_dir)) for p in valid_images])
def test_load_valid(loader, img, caplog):
    image = loader.load(str(img))
    assert image is not None


# @pytest.mark.parametrize("loader", [PILLoader, CV2Loader, SmartLoader, BWLoader], indirect=True)
@pytest.mark.parametrize("img", valid_images, ids=[str(p.relative_to(images_dir)) for p in valid_images])
def test_rotate_valid(loader, img, caplog):
    image = list(loader.rotate(str(img)))
    assert image is not None


# @pytest.mark.parametrize("loader", [PILLoader, CV2Loader, SmartLoader, BWLoader], indirect=True)
@pytest.mark.parametrize("img", invalid_images, ids=[str(p.relative_to(images_dir)) for p in invalid_images])
def test_load_invalid(loader, img, caplog):
    with pytest.raises(InvalidImageError):
        loader.load(str(img))
