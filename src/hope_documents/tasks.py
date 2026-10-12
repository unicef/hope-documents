import logging

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task
def process_analysis_job(job_id: str) -> None:
    from PIL import Image

    from hope_documents.models import AnalysisJob
    from hope_ocr.archive.models import Attribute, Document
    from hope_ocr.ocr.engine import CV2Config, Processor, TSConfig

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

        best_version: str | None = None
        best_score = -1
        best_attributes: list[dict] = []
        version_matched = False

        if documents:
            for doc in documents:
                extracted = []
                score = 0
                for doc_attr in doc.documentattribute_set.all():
                    # Placeholder: region-based extraction is deferred to a future ticket.
                    # Full-image fuzzy search using the attribute name as a proxy.
                    text, _ = processor.find_single(pil_image, doc_attr.attribute.name)
                    value = text.strip()
                    extracted.append({"attribute_name": doc_attr.attribute.name, "extracted_value": value})
                    if value:
                        score += 1
                if score > best_score:
                    best_score = score
                    best_version = doc.version
                    best_attributes = extracted
            if best_score > 0:
                version_matched = True

        if not version_matched:
            best_version = None
            best_attributes = []
            for attr in Attribute.objects.filter(system=True):
                text, _ = processor.find_single(pil_image, attr.name)
                best_attributes.append({"attribute_name": attr.name, "extracted_value": text.strip()})

        if job.callback_url:
            import requests

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
            except Exception:
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
