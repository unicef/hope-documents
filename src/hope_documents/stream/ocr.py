from __future__ import annotations

import logging
from typing import Any

from PIL import Image
from azure.core.exceptions import AzureError
from django.core.files.storage import Storage, storages

from hope_ocr.exceptions import ExtractionError, InvalidImageError
from hope_ocr.ocr.engine import CV2Config, MatchMode, Processor, TSConfig

logger = logging.getLogger(__name__)

ENVELOPE_KEYS = ("correlation_id", "rdp_id", "batch_id", "batch_index", "batch_total")
DOCUMENT_KEYS = ("individual_id", "filename", "pattern")
MAX_OCR_ATTEMPTS = 2
# AzureError covers ResourceNotFoundError (missing blob) and transient Azure IO.
OCR_RETRY_EXC = (OSError, InvalidImageError, ExtractionError, AzureError)


def hope_storage() -> Storage:
    return storages["hope"]


def is_valid_ocr_request(payload: object) -> bool:
    """Return True when the payload matches the ocr.request contract."""
    if not isinstance(payload, dict):
        return False
    if any(key not in payload for key in ENVELOPE_KEYS):
        return False
    documents = payload.get("documents")
    if not isinstance(documents, list):
        return False
    return all(_is_valid_document(item) for item in documents)


def envelope_from(payload: dict[str, Any]) -> dict[str, Any]:
    return {key: payload[key] for key in ENVELOPE_KEYS}


def process_document(filename: str, pattern: str, *, storage: Storage | None = None) -> dict[str, Any]:
    """OCR one document. Retry once on engine/IO failure; a clean miss is ok."""
    backend = storage if storage is not None else hope_storage()
    last_error: str | None = None
    for _attempt in range(MAX_OCR_ATTEMPTS):
        try:
            return _ocr_once(filename, pattern, backend)
        except OCR_RETRY_EXC as exc:
            last_error = f"{type(exc).__name__}: {exc}"
            logger.warning("OCR attempt failed filename=%s error=%s", filename, last_error)
    return {
        "status": "error",
        "found": False,
        "match": None,
        "error": last_error,
    }


def run_ocr_batch(payload: dict[str, Any], *, storage: Storage | None = None) -> dict[str, Any]:
    """Run OCR for every document in a batch and return the ocr.result payload."""
    documents: list[dict[str, Any]] = []
    for item in payload.get("documents") or []:
        outcome = process_document(str(item["filename"]), str(item["pattern"]), storage=storage)
        documents.append({"individual_id": item["individual_id"], **outcome})
    result = envelope_from(payload)
    result["documents"] = documents
    return result


def _is_valid_document(item: object) -> bool:
    if not isinstance(item, dict):
        return False
    return all(key in item for key in DOCUMENT_KEYS)


def _ocr_once(filename: str, pattern: str, storage: Storage) -> dict[str, Any]:
    image = _open_image(filename, storage)
    processor = Processor(ts_config=TSConfig(), cv2_config=CV2Config())
    findings = list(processor.find_text(image, pattern, mode=MatchMode.FIRST))
    if not findings:
        return {"status": "ok", "found": False, "match": None, "error": None}
    finding = findings[0]
    if finding.match:
        return {
            "status": "ok",
            "found": True,
            "match": [finding.match.text, finding.match.distance],
            "error": None,
        }
    return {"status": "ok", "found": False, "match": None, "error": None}


def _open_image(filename: str, storage: Storage) -> Image.Image:
    with storage.open(filename, "rb") as fh:
        image = Image.open(fh)
        image.load()
        return image.copy()
