from __future__ import annotations

import base64
import io
import logging
from typing import Any

from PIL import Image

from hope_ocr.exceptions import ExtractionError, InvalidImageError
from hope_ocr.ocr.engine import CV2Config, MatchMode, Processor, TSConfig

logger = logging.getLogger(__name__)

ENVELOPE_KEYS = ("correlation_id", "rdp_id", "batch_id", "batch_index", "batch_total")
DOCUMENT_KEYS = ("individual_id", "content", "pattern")
MAX_OCR_ATTEMPTS = 2
OCR_RETRY_EXC = (OSError, InvalidImageError, ExtractionError)
# Anything that makes the embedded image undecodable; retrying cannot fix it.
IMAGE_DECODE_EXC = (ValueError, OSError, Image.DecompressionBombError)


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


def process_document(content: str, pattern: str, *, individual_id: object = None) -> dict[str, Any]:
    """OCR one base64-encoded image. Retry once on engine failure; a clean miss is ok.

    An image that cannot be decoded is reported as an error straight away,
    since retrying the same bytes would fail the same way.
    """
    try:
        image = _decode_image(content)
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
        outcome = process_document(item["content"], item["pattern"], individual_id=item["individual_id"])
        documents.append({"individual_id": item["individual_id"], **outcome})
    result = envelope_from(payload)
    result["documents"] = documents
    return result


def _is_valid_document(item: object) -> bool:
    if not isinstance(item, dict):
        return False
    if any(key not in item for key in DOCUMENT_KEYS):
        return False
    return isinstance(item["content"], str) and isinstance(item["pattern"], str)


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


def _decode_image(content: str) -> Image.Image:
    """Decode base64 image bytes (no data-URI prefix) into a fully loaded PIL image."""
    data = base64.b64decode(content)
    with Image.open(io.BytesIO(data)) as image:
        image.load()
        return image.copy()
