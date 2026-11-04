import numpy as np
from PIL import Image

from hope_documents.utils.preprocessing import detect_and_normalise


def _make_image(width: int, height: int, color: tuple) -> Image.Image:
    arr = np.full((height, width, 3), color, dtype=np.uint8)
    return Image.fromarray(arr)


def _make_document_on_background(
    bg_color=(40, 40, 40),
    doc_color=(240, 240, 240),
    img_w=800,
    img_h=600,
    margin=80,
) -> Image.Image:
    """Dark background with a bright white rectangle (the 'document') inset by margin."""
    arr = np.full((img_h, img_w, 3), bg_color, dtype=np.uint8)
    arr[margin : img_h - margin, margin : img_w - margin] = doc_color
    return Image.fromarray(arr)


def test_detect_and_normalise_clean_image():
    """A full-frame clean white image has no detectable background quad; output is the original."""
    image = _make_image(400, 300, (240, 240, 240))
    result = detect_and_normalise(image)
    # Should return a PIL Image without crashing
    assert isinstance(result, Image.Image)
    # Dimensions should be close to original (no major crop applied)
    rw, rh = result.size
    ow, oh = image.size
    assert abs(rw - ow) <= ow * 0.1
    assert abs(rh - oh) <= oh * 0.1


def test_detect_and_normalise_document_on_background():
    """A bright document on a dark background should be cropped to near-document dimensions."""
    margin = 80
    img_w, img_h = 800, 600
    image = _make_document_on_background(img_w=img_w, img_h=img_h, margin=margin)
    result = detect_and_normalise(image)
    assert isinstance(result, Image.Image)
    rw, rh = result.size
    # The result should be smaller than the original (background removed)
    assert rw < img_w
    assert rh < img_h
    # And reasonably close to the document's actual size
    expected_w = img_w - 2 * margin
    expected_h = img_h - 2 * margin
    assert abs(rw - expected_w) <= expected_w * 0.2
    assert abs(rh - expected_h) <= expected_h * 0.2


def test_detect_and_normalise_fallback_no_quad():
    """A noisy gradient image with no clear document edges returns the original image."""
    arr = np.random.randint(100, 160, (300, 400, 3), dtype=np.uint8)
    image = Image.fromarray(arr)
    result = detect_and_normalise(image)
    assert isinstance(result, Image.Image)
    # Should return original dimensions (no quad detected)
    assert result.size == image.size


def test_detect_and_normalise_caps_output_at_1500px():
    """Images larger than 1500px on the long dimension are downscaled before processing."""
    large = _make_image(3000, 2000, (240, 240, 240))
    result = detect_and_normalise(large)
    assert max(result.size) <= 1500
