from unittest.mock import MagicMock

import pytest
from PIL import Image as PILImage

from hope_documents.archive.region import BoundingBox
from hope_documents.llm.extractor import LLMAttributeExtractor


def _image() -> PILImage.Image:
    return PILImage.new("RGB", (200, 100), color="white")


def _make_extractor(return_value: str) -> LLMAttributeExtractor:
    backend = MagicMock()
    backend.complete.return_value = return_value
    return LLMAttributeExtractor(backend)


@pytest.mark.django_db
def test_returns_value_on_high_confidence():
    ex = _make_extractor('{"value": "BIANCA", "confidence": 0.9}')
    assert ex.extract_attribute(_image(), "first_name", None) == "BIANCA"


@pytest.mark.django_db
def test_returns_empty_on_low_confidence():
    ex = _make_extractor('{"value": "X", "confidence": 0.3}')
    assert ex.extract_attribute(_image(), "first_name", None) == ""


@pytest.mark.django_db
def test_strips_markdown_fence_with_language():
    ex = _make_extractor('```json\n{"value": "ABC", "confidence": 0.95}\n```')
    assert ex.extract_attribute(_image(), "first_name", None) == "ABC"


@pytest.mark.django_db
def test_strips_markdown_fence_no_language():
    ex = _make_extractor('```\n{"value": "ABC", "confidence": 0.95}\n```')
    assert ex.extract_attribute(_image(), "first_name", None) == "ABC"


@pytest.mark.django_db
def test_returns_empty_on_json_decode_error():
    ex = _make_extractor("not json at all")
    assert ex.extract_attribute(_image(), "first_name", None) == ""


@pytest.mark.django_db
def test_returns_empty_on_backend_error():
    backend = MagicMock()
    backend.complete.side_effect = RuntimeError("connection refused")
    ex = LLMAttributeExtractor(backend)
    assert ex.extract_attribute(_image(), "first_name", None) == ""


@pytest.mark.django_db
def test_uses_full_image_not_crop():
    """Backend must receive the original full image even when a region is provided."""
    backend = MagicMock()
    backend.complete.return_value = '{"value": "X", "confidence": 0.9}'
    ex = LLMAttributeExtractor(backend)
    img = _image()
    region = BoundingBox.from_rect(10, 10, 50, 30)
    ex.extract_attribute(img, "first_name", region)
    called_image = backend.complete.call_args[0][1]
    assert called_image is img


@pytest.mark.django_db
def test_confidence_above_one_passes():
    ex = _make_extractor('{"value": "X", "confidence": 1.5}')
    assert ex.extract_attribute(_image(), "first_name", None) == "X"


@pytest.mark.django_db
def test_confidence_negative_fails():
    ex = _make_extractor('{"value": "X", "confidence": -0.1}')
    assert ex.extract_attribute(_image(), "first_name", None) == ""


@pytest.mark.django_db
def test_null_value_returns_empty():
    """JSON null value must never be coerced to the string "None"."""
    ex = _make_extractor('{"value": null, "confidence": 0.9}')
    assert ex.extract_attribute(_image(), "first_name", None) == ""
