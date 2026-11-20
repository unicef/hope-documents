import base64
import pathlib
from typing import Any

import requests as http_client
from django.core.files.base import ContentFile
from django.shortcuts import get_object_or_404
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiParameter,
    extend_schema,
    extend_schema_field,
    inline_serializer,
)
from rest_framework import serializers as drf_serializers
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from hope_documents.api.permissions import CanAnalyzeDocuments
from hope_documents.api.serializers.analyze import AnalysisJobStatusSerializer, AnalyzeInputSerializer
from hope_documents.models import AnalysisJob
from hope_documents.tasks import process_analysis_job


@extend_schema_field({"type": "string", "format": "uri", "example": ""})
class _OptionalURLField(drf_serializers.URLField):
    pass


@extend_schema_field({"type": "string", "example": ""})
class _OptionalCharField(drf_serializers.CharField):
    pass


_CONTENT_TYPE_EXT: dict[str, str] = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
}


def _resolve_image(data: dict) -> Any:
    if data.get("image_file"):
        return data["image_file"]
    if data.get("image_url"):
        try:
            resp = http_client.get(data["image_url"], timeout=10)  # TODO: add auth header passthrough
            resp.raise_for_status()
            ct = resp.headers.get("Content-Type", "").split(";")[0].strip()
            ext = _CONTENT_TYPE_EXT.get(ct, ".png")
            return ContentFile(resp.content, name=f"url_image{ext}")
        except http_client.RequestException:
            return None
    if data.get("image_base64"):
        raw = data["image_base64"]
        ext = ".png"
        if "," in raw:
            prefix, raw = raw.split(",", 1)
            ct = prefix.split(":")[1].split(";")[0] if ":" in prefix else ""
            ext = _CONTENT_TYPE_EXT.get(ct, ".png")
        content = base64.b64decode(raw)
        return ContentFile(content, name=f"base64_image{ext}")
    return None


_EXAMPLE_ATTRIBUTES = [
    {"attribute_name": "first_name", "extracted_value": "Test"},
    {"attribute_name": "last_name", "extracted_value": "Sample"},
    {"attribute_name": "document_number", "extracted_value": "AA0000000"},
    {"attribute_name": "date_of_birth", "extracted_value": "1985-06-15"},
]

_EXAMPLE_JOB_COMPLETED = {
    "job_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "status": "completed",
    "document_type": "PAS",
    "country": "AA",
    "validation_mode": "fall_back_to_best_match",
    "version": "v1",
    "version_matched": True,
    "attributes": _EXAMPLE_ATTRIBUTES,
    "error": None,
}


class AnalyzeView(APIView):
    permission_classes = (CanAnalyzeDocuments,)
    serializer_class = AnalyzeInputSerializer

    @extend_schema(
        operation_id="analyze_create",
        summary="Submit a document image for attribute extraction",
        description=(
            "Accepts a document image and queues an extraction job.\n\n"
            "**Image input — provide exactly one of:**\n"
            "- `image_file` — multipart file upload\n"
            "- `image_url` — publicly accessible URL\n"
            "- `image_base64` — base64-encoded bytes (optionally with a data URI prefix)\n\n"
            "**Async (default):** returns a `job_id` immediately (HTTP 202). "
            "Poll `GET /api/analyze/{job_id}/` for the result.\n\n"
            "**Sync:** add `?sync=true` to block until extraction completes and receive the "
            "full result in a single call (HTTP 200). Recommended for low-latency "
            "integrations where the image is small."
        ),
        parameters=[
            OpenApiParameter(
                name="sync",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Set to `true` to wait for extraction and return the result immediately.",
                enum=["true"],
            ),
        ],
        request={
            "multipart/form-data": inline_serializer(
                "AnalyzeRequest",
                {
                    "image_file": drf_serializers.ImageField(required=False),
                    "image_url": _OptionalURLField(required=False),
                    "image_base64": _OptionalCharField(required=False),
                    "document_type": drf_serializers.CharField(),
                    "country": drf_serializers.CharField(),
                    "callback_url": _OptionalURLField(required=False),
                    "validation_mode": drf_serializers.ChoiceField(
                        choices=AnalysisJob.ValidationMode.choices,
                        default=AnalysisJob.ValidationMode.FALL_BACK_TO_BEST_MATCH,
                        required=False,
                    ),
                },
            )
        },
        responses={
            202: inline_serializer("AnalyzeAsyncResponse", {"job_id": drf_serializers.UUIDField()}),
            200: AnalysisJobStatusSerializer,
        },
        examples=[
            OpenApiExample(
                "Request — file upload",
                summary="Multipart file upload with document type and country",
                description="Supply exactly one of image_file, image_url, or image_base64.",
                value={
                    "document_type": "PAS",
                    "country": "AA",
                    "validation_mode": "fall_back_to_best_match",
                },
                request_only=True,
            ),
            OpenApiExample(
                "Response — async (202)",
                summary="Job accepted; use the job_id to poll for the result",
                value={"job_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"},
                response_only=True,
                status_codes=["202"],
            ),
            OpenApiExample(
                "Response — sync completed (200)",
                summary="Full result returned immediately when ?sync=true",
                value=_EXAMPLE_JOB_COMPLETED,
                response_only=True,
                status_codes=["200"],
            ),
        ],
    )
    def post(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        serializer = self.serializer_class(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        image_file = _resolve_image(data)
        if image_file is None:
            return Response({"image_url": "Could not fetch image from URL."}, status=status.HTTP_400_BAD_REQUEST)

        job = AnalysisJob.objects.create(
            document_type=data["document_type_obj"],
            country=data["country_obj"],
            callback_url=data.get("callback_url", ""),
            validation_mode=data.get("validation_mode", AnalysisJob.ValidationMode.FALL_BACK_TO_BEST_MATCH),
        )
        ext = pathlib.Path(image_file.name).suffix or ".png"
        job.image.save(f"{job.id}{ext}", image_file, save=True)
        if request.GET.get("sync") == "true":
            process_analysis_job(str(job.id))
            job.refresh_from_db()
            return Response(AnalysisJobStatusSerializer(job).data, status=status.HTTP_200_OK)
        job.queue()
        return Response({"job_id": str(job.id)}, status=status.HTTP_202_ACCEPTED)


class AnalyzeDetailView(APIView):
    permission_classes = (CanAnalyzeDocuments,)

    @extend_schema(
        operation_id="analyze_retrieve",
        summary="Retrieve extraction job status and result",
        description=(
            "Returns the current status of an extraction job. "
            "Poll until `status` is `completed` or `failed`.\n\n"
            "- `pending` / `running` — job is queued or in progress; `attributes` and `error` are null.\n"
            "- `completed` — `attributes` contains the extracted fields; "
            "`version` and `version_matched` are populated.\n"
            "- `failed` — `error` contains the failure message."
        ),
        responses={200: AnalysisJobStatusSerializer},
        examples=[
            OpenApiExample(
                "Completed job",
                summary="Extraction finished — attributes populated",
                value=_EXAMPLE_JOB_COMPLETED,
                response_only=True,
                status_codes=["200"],
            ),
            OpenApiExample(
                "Pending job",
                summary="Job is still queued or running",
                value={
                    "job_id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
                    "status": "pending",
                    "document_type": "PAS",
                    "country": "AA",
                    "validation_mode": "fall_back_to_best_match",
                    "version": None,
                    "version_matched": None,
                    "attributes": None,
                    "error": None,
                },
                response_only=True,
                status_codes=["200"],
            ),
        ],
    )
    def get(self, request: Request, job_id: Any, *args: Any, **kwargs: Any) -> Response:
        job = get_object_or_404(
            AnalysisJob.objects.select_related("document_type", "country"),
            pk=job_id,
        )
        return Response(AnalysisJobStatusSerializer(job).data)
