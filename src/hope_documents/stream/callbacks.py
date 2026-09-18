import json
import logging
from typing import Any

from pika.adapters.blocking_connection import BlockingChannel
from pika.spec import Basic, BasicProperties
from streaming.event import Event

from hope_documents.stream.ocr import is_valid_ocr_request
from hope_documents.stream.tasks import process_ocr_batch

logger = logging.getLogger(__name__)


def handle_event(
    queue_name: str,
    ch: BlockingChannel,
    method: Basic.Deliver,
    properties: BasicProperties,
    body: bytes,
) -> bool:
    """Enqueue one OCR Celery task per batch and acknowledge the message."""
    try:
        payload = _payload_from_body(body)
    except (json.JSONDecodeError, KeyError, TypeError, ValueError):
        logger.exception(
            "Invalid OCR stream event queue=%s routing_key=%s",
            queue_name,
            method.routing_key,
        )
        return True

    if not is_valid_ocr_request(payload):
        logger.error(
            "Invalid ocr.request payload queue=%s routing_key=%s payload=%r",
            queue_name,
            method.routing_key,
            payload,
        )
        return True

    process_ocr_batch.delay(payload)
    logger.info(
        "Queued OCR batch queue=%s correlation_id=%s batch_id=%s",
        queue_name,
        payload.get("correlation_id"),
        payload.get("batch_id"),
    )
    return True


def _payload_from_body(body: bytes) -> dict[str, Any]:
    message = Event.unmarshal(body)
    payload = message.payload
    if not isinstance(payload, dict):
        raise TypeError("stream event payload must be an object")
    return payload
