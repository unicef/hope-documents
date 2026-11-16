from __future__ import annotations

import io
import logging
from typing import Any

from PIL import Image
from azure.core.exceptions import AzureError
from django.core.exceptions import SuspiciousOperation
from django.core.files.storage import storages

from hope_ocr.exceptions import ExtractionError, InvalidImageError
from hope_ocr.ocr.engine import CV2Config, MatchMode, Processor, TSConfig

logger = logging.getLogger(__name__)

ENVELOPE_KEYS = ("correlation_id", "rdp_id", "batch_id", "batch_index", "batch_total")
DOCUMENT_KEYS = ("individual_id", "filename", "pattern")
HOPE_STORAGE_ALIAS = "hope"
MAX_OCR_ATTEMPTS = 2
OCR_RETRY_EXC = (OSError, InvalidImageError, ExtractionError)
# The Azure client already retries transient failures, so whatever reaches us is final.
# The Azure backend rejects invalid blob names with SuspiciousOperation or ValueError.
BLOB_READ_EXC = (AzureError, OSError, SuspiciousOperation, ValueError)
# Anything that makes the stored image undecodable; retrying cannot fix it.
IMAGE_DECODE_EXC = (ValueError, OSError, Image.DecompressionBombError)


def ocr_request_error(payload: object) -> str | None:
    """Return why the payload breaks the ocr.request contract, or None when it is valid.

    The reason names keys and positions only, never values: documents carry the
    document number, which must not end up in logs.
    """
    if not isinstance(payload, dict):
        return f"payload is {type(payload).__name__}, expected object"
    if missing := [key for key in ENVELOPE_KEYS if key not in payload]:
        return f"missing envelope keys: {', '.join(missing)}"
    documents = payload.get("documents")
    if not isinstance(documents, list):
        return "documents is not a list"
    for index, item in enumerate(documents):
        if reason := _document_error(item):
            return f"documents[{index}]: {reason}"
    return None


def is_valid_ocr_request(payload: object) -> bool:
    """Return True when the payload matches the ocr.request contract."""
    return ocr_request_error(payload) is None


def envelope_from(payload: dict[str, Any]) -> dict[str, Any]:
    return {key: payload[key] for key in ENVELOPE_KEYS}


def process_document(filename: str, pattern: str, *, individual_id: object = None) -> dict[str, Any]:
    """OCR one image read from the shared HOPE storage. Retry once on engine failure; a clean miss is ok.

    An image that cannot be read or decoded is reported as an error straight away,
    since retrying the same blob would fail the same way.
    """
    try:
        data = read_document(filename)
    except BLOB_READ_EXC as exc:
        error = f"{type(exc).__name__}: {next(iter(str(exc).splitlines()), '')}"
        logger.warning("OCR image read failed individual_id=%s filename=%s error=%s", individual_id, filename, error)
        return _error(error)

    try:
        image = _decode_image(data)
    except IMAGE_DECODE_EXC as exc:
        error = f"{type(exc).__name__}: {exc}"
        logger.warning("OCR image decode failed individual_id=%s error=%s", individual_id, error)
        return _error(error)

    last_error: str | None = None
    for _attempt in range(MAX_OCR_ATTEMPTS):
        try:
            return _ocr_once(image, pattern)
        except OCR_RETRY_EXC as exc:
            last_error = f"{type(exc).__name__}: {exc}"
            logger.warning("OCR attempt failed individual_id=%s error=%s", individual_id, last_error)
    return _error(last_error)


def run_ocr_batch(payload: dict[str, Any]) -> dict[str, Any]:
    """Run OCR for every document in a batch and return the ocr.result payload."""
    documents: list[dict[str, Any]] = []
    for item in payload.get("documents") or []:
        outcome = process_document(item["filename"], item["pattern"], individual_id=item["individual_id"])
        documents.append({"individual_id": item["individual_id"], **outcome})
    result = envelope_from(payload)
    result["documents"] = documents
    return result


def _document_error(item: object) -> str | None:
    if not isinstance(item, dict):
        return f"is {type(item).__name__}, expected object"
    if missing := [key for key in DOCUMENT_KEYS if key not in item]:
        return f"missing keys: {', '.join(missing)}"
    if not (isinstance(item["filename"], str) and item["filename"]):
        return "filename is not a non-empty string"
    if not isinstance(item["pattern"], str):
        return "pattern is not a string"
    return None


def _error(error: str | None) -> dict[str, Any]:
    return {"status": "error", "found": False, "match": None, "error": error}


def _ocr_once(image: Image.Image, pattern: str) -> dict[str, Any]:
    processor = Processor(ts_config=TSConfig(), cv2_config=CV2Config())
    findings = list(processor.find_text(image, pattern, mode=MatchMode.FIRST, debug=True))
    if not findings:
        return _miss_or_error(processor)
    finding = findings[0]
    if finding.match:
        return {
            "status": "ok",
            "found": True,
            "match": [finding.match.text, finding.match.distance],
            "error": None,
        }
    return {"status": "ok", "found": False, "match": None, "error": None}


def _miss_or_error(processor: Processor) -> dict[str, Any]:
    """Tell a clean miss apart from a scan where every attempt failed.

    find_text() records extraction errors on each attempt instead of raising, and
    in FIRST mode it yields nothing unless it matched, so both outcomes reach us
    as an empty result. debug=True is what keeps the per-attempt errors around.
    """
    attempts = processor.debug_info.iterations
    if attempts and all(attempt.error for attempt in attempts):
        return {"status": "error", "found": False, "match": None, "error": attempts[-1].error}
    return {"status": "ok", "found": False, "match": None, "error": None}


def read_document(filename: str) -> bytes:
    """Return the bytes Country Workspace stored under `filename` in the shared HOPE storage."""
    with storages[HOPE_STORAGE_ALIAS].open(filename, "rb") as blob:
        return blob.read()


def _decode_image(data: bytes) -> Image.Image:
    """Decode image bytes into a fully loaded PIL image."""
    with Image.open(io.BytesIO(data)) as image:
        image.load()
        return image.copy()
