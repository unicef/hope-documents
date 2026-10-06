from unittest.mock import patch

import pytest

from hope_documents.stream.ocr import is_valid_ocr_request, process_document, run_ocr_batch
from hope_documents.stream.publish import OCR_RESULT_ROUTING_KEY
from hope_documents.stream.tasks import process_ocr_batch
from hope_ocr.exceptions import ExtractionError
from hope_ocr.ocr.diff import Match
from hope_ocr.ocr.engine import SearchInfo


def _finding(*, found: bool) -> SearchInfo:
    match = Match(text="ID-987654", distance=0.0) if found else None
    return SearchInfo(loader="PILLoader", match=match)


def _failed_attempt(error: str = "ExtractionError: ") -> SearchInfo:
    attempt = SearchInfo(loader="PILLoader")
    attempt.error = error
    return attempt


@patch("hope_documents.stream.tasks.publish")
@patch("hope_documents.stream.ocr.process_document")
def test_process_ocr_batch_copies_envelope_and_publishes(mock_process_document, mock_publish, request_payload):
    mock_process_document.return_value = {
        "status": "ok",
        "found": True,
        "match": ["ID-987654", 0.0],
        "error": None,
    }

    result = process_ocr_batch(request_payload)

    assert result["correlation_id"] == "corr-1"
    assert result["rdp_id"] == 123
    assert result["batch_id"] == "batch-1"
    assert result["batch_index"] == 1
    assert result["batch_total"] == 1
    assert result["documents"] == [
        {
            "individual_id": 456,
            "status": "ok",
            "found": True,
            "match": ["ID-987654", 0.0],
            "error": None,
        }
    ]
    mock_publish.assert_called_once_with(OCR_RESULT_ROUTING_KEY, result)


@patch("hope_documents.stream.ocr._decode_image")
@patch("hope_documents.stream.ocr.Processor")
def test_process_document_found_true(mock_processor_cls, mock_decode_image, image_b64):
    mock_processor_cls.return_value.find_text.return_value = [_finding(found=True)]

    result = process_document(image_b64, "ID-987654")

    assert result == {
        "status": "ok",
        "found": True,
        "match": ["ID-987654", 0.0],
        "error": None,
    }
    mock_decode_image.assert_called_once_with(image_b64)


@patch("hope_documents.stream.ocr._decode_image")
@patch("hope_documents.stream.ocr.Processor")
def test_process_document_found_false_is_ok(mock_processor_cls, mock_decode_image, image_b64):
    processor = mock_processor_cls.return_value
    processor.find_text.return_value = []
    processor.debug_info.iterations = [_finding(found=False), _finding(found=False)]

    result = process_document(image_b64, "ID-987654")

    assert result["status"] == "ok"
    assert result["found"] is False
    assert result["match"] is None
    assert result["error"] is None


@patch("hope_documents.stream.ocr._decode_image")
@patch("hope_documents.stream.ocr.Processor")
def test_process_document_all_attempts_failed_is_error(mock_processor_cls, mock_decode_image, image_b64):
    processor = mock_processor_cls.return_value
    processor.find_text.return_value = []
    processor.debug_info.iterations = [
        _failed_attempt("ExtractionError: "),
        _failed_attempt("ExtractionError: timeout"),
    ]

    result = process_document(image_b64, "ID-987654")

    assert result["status"] == "error"
    assert result["found"] is False
    assert result["match"] is None
    assert result["error"] == "ExtractionError: timeout"


@patch("hope_documents.stream.ocr._decode_image")
@patch("hope_documents.stream.ocr.Processor")
def test_process_document_partial_attempt_failure_is_ok(mock_processor_cls, mock_decode_image, image_b64):
    processor = mock_processor_cls.return_value
    processor.find_text.return_value = []
    processor.debug_info.iterations = [_failed_attempt(), _finding(found=False)]

    result = process_document(image_b64, "ID-987654")

    assert result["status"] == "ok"
    assert result["error"] is None


@patch("hope_documents.stream.ocr.Processor")
def test_process_document_retries_once_then_errors(mock_processor_cls, image_b64):
    mock_processor_cls.return_value.find_text.side_effect = ExtractionError("tesseract unavailable")

    result = process_document(image_b64, "ID-987654")

    assert result["status"] == "error"
    assert result["found"] is False
    assert result["match"] is None
    assert result["error"] == "ExtractionError: tesseract unavailable"
    assert mock_processor_cls.return_value.find_text.call_count == 2


@patch("hope_documents.stream.ocr.Processor")
def test_process_document_retries_then_succeeds(mock_processor_cls, image_b64):
    mock_processor_cls.return_value.find_text.side_effect = [
        ExtractionError("transient"),
        [_finding(found=True)],
    ]

    result = process_document(image_b64, "ID-987654")

    assert result["status"] == "ok"
    assert result["found"] is True
    assert mock_processor_cls.return_value.find_text.call_count == 2


@patch("hope_documents.stream.tasks.publish")
def test_empty_batch_publishes_empty_documents(mock_publish, request_payload):
    request_payload["documents"] = []

    result = process_ocr_batch(request_payload)

    assert result["documents"] == []
    assert result["correlation_id"] == "corr-1"
    mock_publish.assert_called_once_with(OCR_RESULT_ROUTING_KEY, result)


@patch("hope_documents.stream.ocr.process_document")
def test_run_ocr_batch_keeps_individual_id(mock_process_document, request_payload):
    mock_process_document.return_value = {
        "status": "ok",
        "found": False,
        "match": None,
        "error": None,
    }

    result = run_ocr_batch(request_payload)

    assert result["documents"][0]["individual_id"] == 456
    mock_process_document.assert_called_once_with(
        request_payload["documents"][0]["content"], "ID-987654", individual_id=456
    )


@patch("hope_ocr.ocr.reader.Reader.extract", side_effect=ExtractionError("tesseract unavailable"))
def test_real_engine_failing_on_every_attempt_is_error(mock_extract, image_b64):
    """Drives the real engine: find_text swallows extraction errors and yields nothing."""
    result = process_document(image_b64, "ID-987654")

    assert result["status"] == "error"
    assert "tesseract unavailable" in result["error"]


@patch("hope_ocr.ocr.reader.Reader.extract", return_value="some unrelated text")
def test_real_engine_reading_without_a_match_is_ok(mock_extract, image_b64):
    result = process_document(image_b64, "ID-987654")

    assert result["status"] == "ok"
    assert result["found"] is False
    assert result["error"] is None


@pytest.mark.parametrize("content", ["not base64 !!!", "aGVsbG8=", ""])
@patch("hope_documents.stream.ocr.Processor")
def test_process_document_undecodable_image_is_error_without_retry(mock_processor_cls, content):
    result = process_document(content, "ID-987654")

    assert result["status"] == "error"
    assert result["found"] is False
    assert result["match"] is None
    assert result["error"]
    mock_processor_cls.assert_not_called()


def test_is_valid_ocr_request_accepts_embedded_image(request_payload):
    assert is_valid_ocr_request(request_payload) is True


def test_is_valid_ocr_request_rejects_blob_filename_contract(request_payload):
    document = request_payload["documents"][0]
    document["filename"] = "media/456.jpg"
    del document["content"]

    assert is_valid_ocr_request(request_payload) is False


def test_is_valid_ocr_request_rejects_non_string_content(request_payload):
    request_payload["documents"][0]["content"] = None

    assert is_valid_ocr_request(request_payload) is False
