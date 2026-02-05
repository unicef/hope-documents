import base64
from io import BytesIO

import pytest
from PIL import Image

from hope_ocr.exceptions import InvalidImageError
from hope_ocr.utils.image import get_image, get_image_base64


@pytest.fixture
def dummy_image_path(tmp_path):
    """Create a dummy image file and return its path."""
    path = tmp_path / "test.png"
    image = Image.new("RGB", (10, 10), color="red")
    image.save(path, "PNG")
    return path


def test_get_image_base64_from_path(dummy_image_path):
    """Test get_image_base64 with a Path object."""
    base64_string = get_image_base64(dummy_image_path)
    assert base64_string.startswith("data:image/png;base64,")
    # Small check to see if it's a valid base64
    base64.b64decode(base64_string.split(",")[1])


def test_get_image_base64_from_pil_image():
    """Test get_image_base64 with a PIL Image object."""
    image = Image.new("RGB", (10, 10), color="blue")
    base64_string = get_image_base64(image)
    assert base64_string.startswith("data:image/png;base64,")
    base64.b64decode(base64_string.split(",")[1])


def test_get_image_base64_from_bytesio():
    """Test get_image_base64 with a BytesIO object."""
    image_file = BytesIO()
    image = Image.new("RGB", (10, 10), color="green")
    image.save(image_file, format="PNG")
    image_file.seek(0)
    base64_string = get_image_base64(image_file)
    assert base64_string.startswith("data:image/png;base64,")
    base64.b64decode(base64_string.split(",")[1])


def test_get_image_base64_unsupported_type():
    """Test get_image_base64 with an unsupported input type."""
    with pytest.raises(ValueError, match="Unsupported"):
        get_image_base64(123)


def test_get_image_valid(dummy_image_path):
    """Test get_image with a valid image file."""
    image = get_image(str(dummy_image_path))
    assert isinstance(image, Image.Image)


def test_get_image_invalid(tmp_path):
    """Test get_image with an invalid image file."""
    invalid_file = tmp_path / "invalid.txt"
    invalid_file.write_text("this is not an image")
    with pytest.raises(InvalidImageError):
        get_image(str(invalid_file))
