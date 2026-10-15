import logging
import re

import requests
from PIL import Image
from celery import shared_task
from django.utils import timezone

from hope_documents.exception import ValidationFailedError
from hope_documents.models import AnalysisJob
from hope_ocr.archive.models import Attribute, Document
from hope_ocr.ocr.engine import CV2Config, Processor, TSConfig

logger = logging.getLogger(__name__)


def _validate_attribute(
    attribute_name: str,
    value: str,
    expression: str | None,
    validation_mode: str,
    extracted: list[dict],
) -> bool:
    """Append the attribute result to extracted. Returns True if the value counts toward version score."""
    is_valid = bool(re.fullmatch(expression, value)) if (expression and value) else True

    if validation_mode == AnalysisJob.ValidationMode.FAIL_ANALYSIS and not is_valid:
        raise ValidationFailedError(
            f"Attribute '{attribute_name}' value '{value}' failed validation."
        )
    if validation_mode == AnalysisJob.ValidationMode.KEEP_VALUE_MARK_INVALID:
        extracted.append({"attribute_name": attribute_name, "extracted_value": value, "is_valid": is_valid})
        return bool(value)
    if validation_mode == AnalysisJob.ValidationMode.TREAT_AS_NOT_FOUND and not is_valid:
        extracted.append({"attribute_name": attribute_name, "extracted_value": ""})
        return False
    extracted.append({"attribute_name": attribute_name, "extracted_value": value})
    if validation_mode == AnalysisJob.ValidationMode.FALL_BACK_TO_BEST_MATCH and not is_valid:
        return False
    return bool(value)


def _match_documents(
    processor: Processor,
    pil_image: Image.Image,
    documents: list[Document],
    validation_mode: str,
) -> tuple[str | None, list[dict], bool]:
    best_version: str | None = None
    best_score = -1
    best_attributes: list[dict] = []
    version_matched = False

    for doc in documents:
        extracted: list[dict] = []
        score = 0
        for doc_attr in doc.documentattribute_set.all():
            # Placeholder: region-based extraction is deferred to a future ticket.
            # Full-image fuzzy search using the attribute name as a proxy.
            text, _ = processor.find_single(pil_image, doc_attr.attribute.name)
            value = text.strip()
            counts = _validate_attribute(
                doc_attr.attribute.name,
                value,
                doc_attr.validation_expression,
                validation_mode,
                extracted,
            )
            if counts:
                score += 1
        if score > best_score:
            best_score = score
            best_version = doc.version
            best_attributes = extracted

    if best_score > 0:
        version_matched = True

    return best_version, best_attributes, version_matched


def _generic_fallback(processor: Processor, pil_image: Image.Image) -> list[dict]:
    result = []
    for attr in Attribute.objects.filter(system=True):
        text, _ = processor.find_single(pil_image, attr.name)
        result.append({"attribute_name": attr.name, "extracted_value": text.strip()})
    return result


@shared_task
def process_analysis_job(job_id: str) -> None:
    job = AnalysisJob.objects.select_related("document_type", "country").get(pk=job_id)

    try:
        job.status = AnalysisJob.Status.RUNNING
        job.save(update_fields=["status"])

        with job.image.open("rb") as fh:
            pil_image = Image.open(fh)
            pil_image.load()

        processor = Processor(ts_config=TSConfig(), cv2_config=CV2Config())
        documents = list(
            Document.objects.filter(
                document_type=job.document_type,
                country=job.country,
            ).prefetch_related("documentattribute_set__attribute")
        )

        if documents:
            best_version, best_attributes, version_matched = _match_documents(
                processor, pil_image, documents, job.validation_mode
            )
        else:
            best_version, best_attributes, version_matched = None, [], False

        if not version_matched:
            best_version = None
            best_attributes = _generic_fallback(processor, pil_image)

        if job.callback_url:
            payload = {
                "job_id": str(job.id),
                "status": "completed",
                "document_type": job.document_type.code,
                "country": job.country.code2,
                "version": best_version,
                "version_matched": version_matched,
                "attributes": best_attributes,
            }
            try:
                requests.post(job.callback_url, json=payload, timeout=10)
            except requests.RequestException:
                logger.warning("Callback POST failed for job %s", job_id)

        job.status = AnalysisJob.Status.COMPLETED
        job.matched_version = best_version or ""
        job.version_matched = version_matched
        job.result = best_attributes
        job.completed_at = timezone.now()
        job.save(update_fields=["status", "matched_version", "version_matched", "result", "completed_at"])

    except Exception as exc:
        job.status = AnalysisJob.Status.FAILED
        job.error = str(exc)
        job.save(update_fields=["status", "error"])
        raise
