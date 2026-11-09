import logging
import re

import requests
from PIL import Image
from celery import shared_task
from django.core.exceptions import ImproperlyConfigured
from django.utils import timezone
from django.utils.module_loading import import_string

from hope_documents.archive.models import Attribute, Document
from hope_documents.exceptions import ValidationFailedError
from hope_documents.extractors import AttributeExtractor, ChainedAttributeExtractor, OCRAttributeExtractor
from hope_documents.llm.extractor import LLMAttributeExtractor
from hope_documents.models import AnalysisJob
from hope_documents.ocr.engine import CV2Config, Processor, TSConfig
from hope_documents.utils.preprocessing import detect_and_normalise

logger = logging.getLogger(__name__)


def _build_extractor(processor: Processor) -> AttributeExtractor:
    from django.conf import settings

    items: list[AttributeExtractor] = []
    for name in settings.EXTRACTOR_CHAIN:
        if name == "ocr":
            items.append(OCRAttributeExtractor(processor))
        elif name == "llm":
            if not settings.LLM_BACKEND:
                raise ImproperlyConfigured(
                    "HOPE_EXTRACTOR_CHAIN includes 'llm' but HOPE_LLM_BACKEND is not configured"
                )
            cfg = settings.LLM_BACKEND.copy()
            backend_cls = import_string(cfg.pop("provider"))
            items.append(LLMAttributeExtractor(backend_cls(**cfg)))
    if not items:
        raise ImproperlyConfigured(
            f"HOPE_EXTRACTOR_CHAIN produced no valid extractors (value: {settings.EXTRACTOR_CHAIN!r}). "
            "Valid names are 'ocr' and 'llm'."
        )
    if len(items) == 1:
        return items[0]
    return ChainedAttributeExtractor(items)


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
        raise ValidationFailedError(f"Attribute '{attribute_name}' value '{value}' failed validation.")
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
    extractor: AttributeExtractor,
    pil_image: Image.Image,
    documents: list[Document],
    validation_mode: str,
) -> tuple[str | None, list[dict], bool]:
    best_version: str | None = None
    best_score = -1
    best_attributes: list[dict] = []
    version_matched = False

    proc_w, proc_h = pil_image.size

    for doc in documents:
        extracted: list[dict] = []
        score = 0
        sx = proc_w / doc.reference_width if doc.reference_width else 1.0
        sy = proc_h / doc.reference_height if doc.reference_height else 1.0
        for doc_attr in doc.documentattribute_set.all():
            scaled_region = doc_attr.region.scale(sx, sy) if doc_attr.region else None
            value = extractor.extract_attribute(pil_image, doc_attr.attribute.name, scaled_region)
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


def _generic_fallback(extractor: AttributeExtractor, pil_image: Image.Image) -> list[dict]:
    result = []
    for attr in Attribute.objects.filter(system=True):
        value = extractor.extract_attribute(pil_image, attr.name, None)
        result.append({"attribute_name": attr.name, "extracted_value": value})
    return result


@shared_task
def process_analysis_job(pk: str, version: int | None = None) -> None:
    """Run OCR extraction for a single AnalysisJob, update its status fields, and POST to callback_url if set."""
    job = AnalysisJob.objects.select_related("document_type", "country").get(pk=pk)

    try:
        job.status = AnalysisJob.Status.RUNNING
        job.save(update_fields=["status"])

        with job.image.open("rb") as fh:
            pil_image = Image.open(fh)
            pil_image.load()

        pil_image = detect_and_normalise(pil_image)
        processor = Processor(ts_config=TSConfig(), cv2_config=CV2Config())
        extractor = _build_extractor(processor)
        documents = list(
            Document.objects.filter(
                document_type=job.document_type,
                country=job.country,
            ).prefetch_related("documentattribute_set__attribute")
        )

        if documents:
            best_version, best_attributes, version_matched = _match_documents(
                extractor, pil_image, documents, job.validation_mode
            )
        else:
            best_version, best_attributes, version_matched = None, [], False

        if not version_matched:
            best_version = None
            best_attributes = _generic_fallback(extractor, pil_image)

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
                logger.warning("Callback POST failed for job %s", pk)

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
