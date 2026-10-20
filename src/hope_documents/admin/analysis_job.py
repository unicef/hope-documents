from django.contrib import admin
from unfold.admin import ModelAdmin

from hope_documents.models import AnalysisJob


@admin.register(AnalysisJob)
class AnalysisJobAdmin(ModelAdmin):
    list_display = ["id", "status", "document_type", "country", "validation_mode", "created_at", "completed_at"]
    list_filter = ["status", "document_type", "country", "validation_mode"]
    search_fields = ["id"]
    readonly_fields = [
        "id",
        "status",
        "document_type",
        "country",
        "image",
        "validation_mode",
        "callback_url",
        "matched_version",
        "version_matched",
        "result",
        "error",
        "created_at",
        "completed_at",
    ]
    ordering = ["-created_at"]
