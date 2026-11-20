import logging
from typing import Any

from celery import Task, shared_task
from celery.utils.time import get_exponential_backoff_interval
from django.conf import settings

from hope_documents.stream.ocr import run_ocr_batch
from hope_documents.stream.publish import OCR_RESULT_ROUTING_KEY, publish

logger = logging.getLogger(__name__)


class OCRResultPublishError(RuntimeError):
    """Publishing hcw.ocr.result failed."""


@shared_task
def process_ocr_batch(payload: dict[str, Any]) -> dict[str, Any]:
    """OCR every document in a batch and publish hcw.ocr.result.

    If publishing fails, hand the computed result to publish_ocr_result, which
    retries delivery with backoff. OCR is never run again for the same batch.
    """
    result = run_ocr_batch(payload)
    if not publish(OCR_RESULT_ROUTING_KEY, result):
        if settings.OCR_RESULT_PUBLISH_MAX_RETRIES <= 0:
            raise OCRResultPublishError(
                f"{OCR_RESULT_ROUTING_KEY}: publish failed correlation_id={result.get('correlation_id')} "
                f"batch_id={result.get('batch_id')}; retries disabled"
            )
        logger.warning(
            "%s: publish failed, scheduling retry correlation_id=%s batch_id=%s",
            OCR_RESULT_ROUTING_KEY,
            result.get("correlation_id"),
            result.get("batch_id"),
        )
        publish_ocr_result.apply_async(args=[result], countdown=_retry_countdown(0))
    return result


@shared_task(bind=True, acks_late=True, reject_on_worker_lost=True)
def publish_ocr_result(self: Task, result: dict[str, Any]) -> None:
    """Retry delivery of an already computed hcw.ocr.result.

    Ack only after the run finishes, so a worker crash mid-run leaves the
    message to be redelivered instead of losing the result. A crash after a
    successful publish can deliver the result twice; consumers must tolerate that.
    """
    if publish(OCR_RESULT_ROUTING_KEY, result):
        logger.info(
            "%s: published after %d retries correlation_id=%s batch_id=%s",
            OCR_RESULT_ROUTING_KEY,
            self.request.retries + 1,
            result.get("correlation_id"),
            result.get("batch_id"),
        )
        return

    # The first attempt happened in process_ocr_batch, so this run is retry number retries + 1.
    attempt = self.request.retries + 1
    max_retries = settings.OCR_RESULT_PUBLISH_MAX_RETRIES
    error = OCRResultPublishError(
        f"{OCR_RESULT_ROUTING_KEY}: publish failed correlation_id={result.get('correlation_id')} "
        f"batch_id={result.get('batch_id')} retry={attempt}/{max_retries}"
    )
    if attempt >= max_retries:
        # Never log the result: documents carry document numbers.
        logger.error("%s; retries exhausted, result not delivered", error)
        raise error
    raise self.retry(exc=error, countdown=_retry_countdown(attempt), max_retries=max_retries)


def _retry_countdown(retries: int) -> int:
    return get_exponential_backoff_interval(
        factor=settings.OCR_RESULT_PUBLISH_RETRY_BACKOFF,
        retries=retries,
        maximum=settings.OCR_RESULT_PUBLISH_RETRY_BACKOFF_MAX,
        full_jitter=True,
    )
