from typing import Any

from celery import shared_task

from hope_documents.stream.ocr import run_ocr_batch
from hope_documents.stream.publish import OCR_RESULT_ROUTING_KEY, publish


@shared_task
def process_ocr_batch(payload: dict[str, Any]) -> dict[str, Any]:
    """OCR every document in a batch and publish hcw.ocr.result."""
    result = run_ocr_batch(payload)
    if not publish(OCR_RESULT_ROUTING_KEY, result):
        raise RuntimeError(
            f"{OCR_RESULT_ROUTING_KEY}: publish failed correlation_id={result.get('correlation_id')} "
            f"batch_id={result.get('batch_id')}"
        )
    return result
