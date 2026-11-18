import base64
from unittest.mock import patch

import pytest
from azure.core.exceptions import ResourceNotFoundError
from django.core.files.base import ContentFile

from hope_documents.stream.ocr import (
    is_valid_ocr_request,
    ocr_request_error,
    process_document,
    read_document,
    run_ocr_batch,
)
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
def test_process_document_found_true(mock_processor_cls, mock_decode_image, image_filename, image_bytes):
    mock_processor_cls.return_value.find_text.return_value = [_finding(found=True)]

    result = process_document(image_filename, "ID-987654")

    assert result == {
        "status": "ok",
        "found": True,
        "match": ["ID-987654", 0.0],
        "error": None,
    }
    mock_decode_image.assert_called_once_with(image_bytes)


def test_read_document_reads_from_hope_storage(image_filename, image_bytes):
    assert read_document(image_filename) == image_bytes


@pytest.mark.parametrize("filename", ["2024/missing.png", "../outside.png"])
@patch("hope_documents.stream.ocr.Processor")
def test_process_document_unreadable_blob_is_error_without_retry(mock_processor_cls, filename):
    result = process_document(filename, "ID-987654")

    assert result["status"] == "error"
    assert result["found"] is False
    assert result["match"] is None
    assert result["error"]
    mock_processor_cls.assert_not_called()


@pytest.mark.parametrize(
    ("filename", "error"),
    [("../outside.png", "SuspiciousOperation: "), ("x" * 1025, "ValueError: ")],
)
@patch("hope_documents.stream.ocr.Processor")
def test_process_document_invalid_azure_blob_name_is_error(mock_processor_cls, settings, filename, error):
    """The Azure backend rejects these names before sending any request."""
    settings.STORAGES = {
        **settings.STORAGES,
        "hope": {
            "BACKEND": "storages.backends.azure_storage.AzureStorage",
            "OPTIONS": {
                "azure_container": "hope",
                "location": "ocr",
                "connection_string": (
                    "DefaultEndpointsProtocol=http;AccountName=devstoreaccount1;AccountKey=a2V5;"
                    "BlobEndpoint=http://127.0.0.1:9/devstoreaccount1;"
                ),
            },
        },
    }

    result = process_document(filename, "ID-987654")

    assert result["status"] == "error"
    assert result["error"].startswith(error)
    mock_processor_cls.assert_not_called()


@patch("hope_documents.stream.ocr.Processor")
def test_process_document_keeps_the_summary_of_an_azure_error(mock_processor_cls, image_filename):
    error = ResourceNotFoundError("The specified blob does not exist.\nRequestId:1\nErrorCode:BlobNotFound")

    with patch("hope_documents.stream.ocr.read_document", side_effect=error):
        result = process_document(image_filename, "ID-987654")

    assert result["error"] == "ResourceNotFoundError: The specified blob does not exist."
    mock_processor_cls.assert_not_called()


@patch("hope_documents.stream.ocr._decode_image")
@patch("hope_documents.stream.ocr.Processor")
def test_process_document_found_false_is_ok(mock_processor_cls, mock_decode_image, image_filename):
    processor = mock_processor_cls.return_value
    processor.find_text.return_value = []
    processor.debug_info.iterations = [_finding(found=False), _finding(found=False)]

    result = process_document(image_filename, "ID-987654")

    assert result["status"] == "ok"
    assert result["found"] is False
    assert result["match"] is None
    assert result["error"] is None


@patch("hope_documents.stream.ocr._decode_image")
@patch("hope_documents.stream.ocr.Processor")
def test_process_document_all_attempts_failed_is_error(mock_processor_cls, mock_decode_image, image_filename):
    processor = mock_processor_cls.return_value
    processor.find_text.return_value = []
    processor.debug_info.iterations = [
        _failed_attempt("ExtractionError: "),
        _failed_attempt("ExtractionError: timeout"),
    ]

    result = process_document(image_filename, "ID-987654")

    assert result["status"] == "error"
    assert result["found"] is False
    assert result["match"] is None
    assert result["error"] == "ExtractionError: timeout"


@patch("hope_documents.stream.ocr._decode_image")
@patch("hope_documents.stream.ocr.Processor")
def test_process_document_partial_attempt_failure_is_ok(mock_processor_cls, mock_decode_image, image_filename):
    processor = mock_processor_cls.return_value
    processor.find_text.return_value = []
    processor.debug_info.iterations = [_failed_attempt(), _finding(found=False)]

    result = process_document(image_filename, "ID-987654")

    assert result["status"] == "ok"
    assert result["error"] is None


@patch("hope_documents.stream.ocr.Processor")
def test_process_document_retries_once_then_errors(mock_processor_cls, image_filename):
    mock_processor_cls.return_value.find_text.side_effect = ExtractionError("tesseract unavailable")

    result = process_document(image_filename, "ID-987654")

    assert result["status"] == "error"
    assert result["found"] is False
    assert result["match"] is None
    assert result["error"] == "ExtractionError: tesseract unavailable"
    assert mock_processor_cls.return_value.find_text.call_count == 2


@patch("hope_documents.stream.ocr.Processor")
def test_process_document_retries_then_succeeds(mock_processor_cls, image_filename):
    mock_processor_cls.return_value.find_text.side_effect = [
        ExtractionError("transient"),
        [_finding(found=True)],
    ]

    result = process_document(image_filename, "ID-987654")

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
        request_payload["documents"][0]["filename"], "ID-987654", individual_id=456
    )


@patch("hope_ocr.ocr.reader.Reader.extract", side_effect=ExtractionError("tesseract unavailable"))
def test_real_engine_failing_on_every_attempt_is_error(mock_extract, image_filename):
    """Drives the real engine: find_text swallows extraction errors and yields nothing."""
    result = process_document(image_filename, "ID-987654")

    assert result["status"] == "error"
    assert "tesseract unavailable" in result["error"]


@patch("hope_ocr.ocr.reader.Reader.extract", return_value="some unrelated text")
def test_real_engine_reading_without_a_match_is_ok(mock_extract, image_filename):
    result = process_document(image_filename, "ID-987654")

    assert result["status"] == "ok"
    assert result["found"] is False
    assert result["error"] is None


@pytest.mark.parametrize("content", [b"not an image", b"hello", b""])
@patch("hope_documents.stream.ocr.Processor")
def test_process_document_undecodable_image_is_error_without_retry(mock_processor_cls, hope_storage, content):
    filename = hope_storage.save("2024/broken.png", ContentFile(content))

    result = process_document(filename, "ID-987654")

    assert result["status"] == "error"
    assert result["found"] is False
    assert result["match"] is None
    assert result["error"]
    mock_processor_cls.assert_not_called()


def test_is_valid_ocr_request_accepts_blob_filename(request_payload):
    assert is_valid_ocr_request(request_payload) is True


def test_is_valid_ocr_request_rejects_embedded_image_contract(request_payload, image_bytes):
    document = request_payload["documents"][0]
    document["content"] = base64.b64encode(image_bytes).decode()
    del document["filename"]

    assert is_valid_ocr_request(request_payload) is False


@pytest.mark.parametrize("filename", [None, 42, ""])
def test_is_valid_ocr_request_rejects_invalid_filename(request_payload, filename):
    request_payload["documents"][0]["filename"] = filename

    assert is_valid_ocr_request(request_payload) is False


def test_ocr_request_error_is_none_for_valid_request(request_payload):
    assert ocr_request_error(request_payload) is None


def test_ocr_request_error_reports_non_object_payload():
    assert ocr_request_error(["not", "a", "dict"]) == "payload is list, expected object"


def test_ocr_request_error_lists_missing_envelope_keys(request_payload):
    del request_payload["batch_id"], request_payload["rdp_id"]

    assert ocr_request_error(request_payload) == "missing envelope keys: rdp_id, batch_id"


def test_ocr_request_error_reports_documents_not_a_list(request_payload):
    request_payload["documents"] = "nope"

    assert ocr_request_error(request_payload) == "documents is not a list"


def test_ocr_request_error_reports_non_object_document(request_payload):
    request_payload["documents"] = ["nope"]

    assert ocr_request_error(request_payload) == "documents[0]: is str, expected object"


def test_ocr_request_error_reports_missing_document_keys(request_payload):
    del request_payload["documents"][0]["filename"]

    assert ocr_request_error(request_payload) == "documents[0]: missing keys: filename"


def test_ocr_request_error_reports_non_string_filename(request_payload):
    request_payload["documents"][0]["filename"] = 42

    assert ocr_request_error(request_payload) == "documents[0]: filename is not a non-empty string"


def test_ocr_request_error_never_includes_document_values(request_payload):
    request_payload["documents"][0]["filename"] = ""

    assert request_payload["documents"][0]["pattern"] not in ocr_request_error(request_payload)
