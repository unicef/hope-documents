import io
from unittest.mock import MagicMock, patch

from PIL import Image
from azure.core.exceptions import ResourceNotFoundError
from django.core.files.base import ContentFile
from django.core.files.storage import FileSystemStorage

from hope_documents.stream.ocr import hope_storage, process_document, run_ocr_batch
from hope_documents.stream.tasks import process_ocr_batch
from hope_ocr.ocr.diff import Match
from hope_ocr.ocr.engine import SearchInfo


def _finding(*, found: bool) -> SearchInfo:
    match = Match(text="ID-987654", distance=0.0) if found else None
    return SearchInfo(loader="PILLoader", match=match)


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
    mock_publish.assert_called_once_with("ocr.result", result)


@patch("hope_documents.stream.ocr._open_image")
@patch("hope_documents.stream.ocr.Processor")
def test_process_document_found_true(mock_processor_cls, mock_open_image):
    mock_processor_cls.return_value.find_text.return_value = [_finding(found=True)]

    result = process_document("media/456.jpg", "ID-987654", storage=MagicMock())

    assert result == {
        "status": "ok",
        "found": True,
        "match": ["ID-987654", 0.0],
        "error": None,
    }
    mock_open_image.assert_called_once()


@patch("hope_documents.stream.ocr._open_image")
@patch("hope_documents.stream.ocr.Processor")
def test_process_document_found_false_is_ok(mock_processor_cls, mock_open_image):
    mock_processor_cls.return_value.find_text.return_value = []

    result = process_document("media/456.jpg", "ID-987654", storage=MagicMock())

    assert result["status"] == "ok"
    assert result["found"] is False
    assert result["match"] is None
    assert result["error"] is None


@patch("hope_documents.stream.ocr._open_image")
def test_process_document_retries_once_then_errors(mock_open_image):
    mock_open_image.side_effect = OSError("blob missing")

    result = process_document("media/456.jpg", "ID-987654", storage=MagicMock())

    assert result["status"] == "error"
    assert result["found"] is False
    assert result["match"] is None
    assert result["error"] == "OSError: blob missing"
    assert mock_open_image.call_count == 2


@patch("hope_documents.stream.ocr._open_image")
@patch("hope_documents.stream.ocr.Processor")
def test_process_document_retries_then_succeeds(mock_processor_cls, mock_open_image):
    mock_open_image.side_effect = [OSError("transient"), MagicMock()]
    mock_processor_cls.return_value.find_text.return_value = [_finding(found=True)]

    result = process_document("media/456.jpg", "ID-987654", storage=MagicMock())

    assert result["status"] == "ok"
    assert result["found"] is True
    assert mock_open_image.call_count == 2


@patch("hope_documents.stream.tasks.publish")
def test_empty_batch_publishes_empty_documents(mock_publish, request_payload):
    request_payload["documents"] = []

    result = process_ocr_batch(request_payload)

    assert result["documents"] == []
    assert result["correlation_id"] == "corr-1"
    mock_publish.assert_called_once_with("ocr.result", result)


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
    mock_process_document.assert_called_once_with("media/456.jpg", "ID-987654", storage=None)


@patch("hope_documents.stream.ocr.storages")
def test_hope_storage_uses_hope_alias(mock_storages):
    backend = MagicMock()
    mock_storages.__getitem__.return_value = backend

    assert hope_storage() is backend
    mock_storages.__getitem__.assert_called_once_with("hope")


@patch("hope_documents.stream.ocr._open_image")
def test_process_document_retries_missing_azure_blob(mock_open_image):
    mock_open_image.side_effect = ResourceNotFoundError("The specified blob does not exist.")
    filename = "AFG/CP-2024/CW_ind_456_national_id_photo.png"

    result = process_document(filename, "ID-987654", storage=MagicMock())

    assert result["status"] == "error"
    assert result["found"] is False
    assert result["match"] is None
    assert "ResourceNotFoundError" in result["error"]
    assert mock_open_image.call_count == 2


@patch("hope_documents.stream.ocr.Processor")
def test_process_document_opens_cw_blob_key(mock_processor_cls, tmp_path):
    storage = FileSystemStorage(location=str(tmp_path))
    key = "AFG/CP-2024/CW_ind_456_national_id_photo.png"
    buf = io.BytesIO()
    Image.new("RGB", (1, 1), color="white").save(buf, format="PNG")
    storage.save(key, ContentFile(buf.getvalue()))
    mock_processor_cls.return_value.find_text.return_value = [_finding(found=True)]

    result = process_document(key, "ID-987654", storage=storage)

    assert result == {
        "status": "ok",
        "found": True,
        "match": ["ID-987654", 0.0],
        "error": None,
    }
