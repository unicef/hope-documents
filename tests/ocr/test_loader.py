from pathlib import Path

import pytest
from PIL import Image

from hope_ocr.exceptions import InvalidImageError
from hope_ocr.ocr.loaders import (
    BWLoader,
    CV2Loader,
    ImprovedLoader,
    Loader,
    PILLoader,
    SmartLoader,
    loader_registry,
)

images_dir = Path(__file__).parent / "images"

valid_images = [
    p for p in images_dir.rglob("*.png") if not p.is_dir() and not p.name.startswith("_")
]
invalid_images = [
    images_dir / "_invalid/_empty.png",
    images_dir / "_invalid/_text.txt",
]


@pytest.fixture(params=loader_registry, ids=[c.__name__ for c in loader_registry])
def loader(request):
    """Fixture to provide all registered loaders."""
    # All loaders accept scale_factor through kwargs or directly.
    return request.param(scale_factor=0.9)


def test_loader_str_representation():
    """Test the __str__ method of loaders."""
    assert str(Loader()) == "Loader()"
    assert str(PILLoader()) == "PILLoader()"
    assert str(CV2Loader()) == "CV2Loader()"
    assert str(SmartLoader()) == "SmartLoader()"


def test_loader_initialization():
    """Test that loaders can be initialized with custom parameters."""
    cv2_loader = CV2Loader(threshold=100)
    assert cv2_loader.threshold == 100

    smart_loader = SmartLoader(block_size=9, c=3)
    assert smart_loader.block_size == 9
    assert smart_loader.c == 3

    bw_loader = BWLoader(block_size=9, c=5)
    assert bw_loader.block_size == 9
    assert bw_loader.c == 5

    improved_loader = ImprovedLoader(scale_factor=2.0, blur_kernel_size=7)
    assert improved_loader.scale_factor == 2.0
    assert improved_loader.blur_kernel_size == 7


def test_pill_loader_process():
    """Test the process method of PILLoader."""
    loader = PILLoader()
    image = Image.new("RGB", (10, 10))
    processed_image = loader.process(image)
    assert processed_image.mode == "L"


def test_cv2_loader_process():
    """Test the process method of CV2Loader."""
    loader = CV2Loader(threshold=128)
    image = Image.new("RGB", (10, 10), color="grey")
    processed_image = loader.process(image)
    assert processed_image.mode == "L"


@pytest.mark.parametrize(
    "img", valid_images, ids=[str(p.relative_to(images_dir)) for p in valid_images]
)
def test_load_valid(loader, img, caplog):
    image = loader.load(str(img))
    assert image is not None
    assert isinstance(image, Image.Image)


@pytest.mark.parametrize(
    "filename", valid_images, ids=[str(p.relative_to(images_dir)) for p in valid_images]
)
def test_rotate_valid(loader, filename, caplog):
    """Test the rotate method of loaders."""
    img = Image.open(filename)
    loader.rotations = [0, 90, 180]
    rotated_images = list(loader.rotate(img))
    assert len(rotated_images) == 3
    for rotated_image, angle in rotated_images:
        assert isinstance(rotated_image, Image.Image)
        assert angle in [0, 90, 180]


@pytest.mark.parametrize(
    "filename",
    invalid_images,
    ids=[str(p.relative_to(images_dir)) for p in invalid_images],
)
def test_load_invalid(loader, filename, caplog):
    with pytest.raises(InvalidImageError):
        loader.load(filename)
