from unittest.mock import MagicMock, patch

import pytest
from PIL import Image as PILImage
from factories.analysis import AnalysisJobFactory
from factories.documents import DocumentAttributeFactory

from hope_documents.archive.region import BoundingBox
from django.core.exceptions import ImproperlyConfigured

from hope_documents.extractors import ChainedAttributeExtractor, OCRAttributeExtractor
from hope_documents.llm.extractor import LLMAttributeExtractor
from hope_documents.ocr.engine import CV2Config, Processor, TSConfig
from hope_documents.tasks import _build_extractor, _match_documents, process_analysis_job


def _small_image() -> PILImage.Image:
    return PILImage.new("RGB", (200, 100), color="white")


@pytest.mark.django_db
def test_match_documents_accepts_preprocessed_image():
    """_match_documents uses the image it receives; pre-processing is the caller's responsibility."""
    da = DocumentAttributeFactory.create()

    extractor = MagicMock()
    captured_images = []

    def fake_extract(image, attr_name, region):
        captured_images.append(image)
        return "value"

    extractor.extract_attribute.side_effect = fake_extract

    pre_processed = _small_image()
    with patch("hope_documents.tasks.detect_and_normalise") as mock_preprocess:
        _match_documents(extractor, pre_processed, [da.document], "default")

    mock_preprocess.assert_not_called()
    assert captured_images[0] is pre_processed


@pytest.mark.django_db
def test_match_documents_scales_region_by_reference_dims():
    """When Document has reference dims, region coords are scaled by processed/reference ratio."""
    bb = BoundingBox.from_rect(10, 20, 100, 50)
    da = DocumentAttributeFactory.create(region=bb)
    da.document.reference_width = 100
    da.document.reference_height = 100
    da.document.save(update_fields=["reference_width", "reference_height"])

    captured = []

    extractor = MagicMock()

    def fake_extract(image, attr_name, region):
        captured.append(region)
        return "value"

    extractor.extract_attribute.side_effect = fake_extract

    # processed image is 200x300 — scale factors: 200/100=2.0, 300/100=3.0
    processed = PILImage.new("RGB", (200, 300), color="white")

    _match_documents(extractor, processed, [da.document], "default")

    assert len(captured) == 1
    region = captured[0]
    assert region is not None
    assert region.top_left.x == pytest.approx(20.0)  # 10 * 2.0
    assert region.top_left.y == pytest.approx(60.0)  # 20 * 3.0


@pytest.mark.django_db
def test_match_documents_no_reference_dims_uses_original_region():
    """When Document has no reference dims, the region is used as-is (scale factor 1.0)."""
    bb = BoundingBox.from_rect(10, 20, 100, 50)
    da = DocumentAttributeFactory.create(region=bb)
    # reference_width/height are None by default

    captured = []
    extractor = MagicMock()

    def fake_extract(image, attr_name, region):
        captured.append(region)
        return "value"

    extractor.extract_attribute.side_effect = fake_extract

    processed = PILImage.new("RGB", (400, 300), color="white")
    _match_documents(extractor, processed, [da.document], "default")

    assert len(captured) == 1
    # No scaling — region should equal original
    assert captured[0] == bb


@pytest.mark.django_db
def test_process_analysis_job_preprocesses_before_fallback():
    """detect_and_normalise is called even when no documents are configured (fallback path)."""
    job = AnalysisJobFactory.create()
    # No Document configured for this job's type/country → documents=[] → fallback path

    processed = PILImage.new("RGB", (200, 100), color="white")
    mock_extractor = MagicMock()
    mock_extractor.extract_attribute.return_value = "test_value"

    with (
        patch("hope_documents.tasks.detect_and_normalise", return_value=processed) as mock_preprocess,
        patch("hope_documents.tasks.OCRAttributeExtractor", return_value=mock_extractor),
    ):
        process_analysis_job(str(job.pk))

    mock_preprocess.assert_called_once()


def _processor() -> Processor:
    return Processor(ts_config=TSConfig(), cv2_config=CV2Config())


def test_build_extractor_ocr_only(settings):
    settings.EXTRACTOR_CHAIN = ["ocr"]
    settings.LLM_BACKEND = None
    result = _build_extractor(_processor())
    assert isinstance(result, OCRAttributeExtractor)


def test_build_extractor_chain(settings):
    settings.EXTRACTOR_CHAIN = ["ocr", "llm"]
    settings.LLM_BACKEND = {
        "provider": "hope_documents.llm.backends.OllamaBackend",
        "host": "http://localhost:11434",
        "model": "llama3.2-vision",
    }
    result = _build_extractor(_processor())
    assert isinstance(result, ChainedAttributeExtractor)


def test_build_extractor_llm_only(settings):
    settings.EXTRACTOR_CHAIN = ["llm"]
    settings.LLM_BACKEND = {
        "provider": "hope_documents.llm.backends.OllamaBackend",
        "host": "http://localhost:11434",
        "model": "llama3.2-vision",
    }
    result = _build_extractor(_processor())
    assert isinstance(result, LLMAttributeExtractor)


def test_build_extractor_llm_no_backend_raises(settings):
    settings.EXTRACTOR_CHAIN = ["llm"]
    settings.LLM_BACKEND = None
    with pytest.raises(ImproperlyConfigured):
        _build_extractor(_processor())
