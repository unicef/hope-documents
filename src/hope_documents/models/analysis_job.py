import uuid

from django.db import models

from hope_ocr.archive.models import Country, DocumentType


class AnalysisJob(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        RUNNING = "running", "Running"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    document_type = models.ForeignKey(DocumentType, on_delete=models.PROTECT, related_name="analysis_jobs")
    country = models.ForeignKey(Country, on_delete=models.PROTECT, related_name="analysis_jobs")
    image = models.FileField(upload_to="analysis_jobs/")
    callback_url = models.URLField(blank=True)
    matched_version = models.CharField(max_length=255, blank=True)
    version_matched = models.BooleanField(null=True, blank=True)
    result = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    error = models.TextField(blank=True)

    class Meta:
        app_label = "hope_documents"
        ordering = ("-created_at",)

    def __str__(self) -> str:
        return f"AnalysisJob({self.id}, {self.status})"