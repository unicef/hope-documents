import base64
import pathlib
from typing import Any

import requests as http_client
from django.core.files.base import ContentFile
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from hope_documents.api.permissions import CanAnalyzeDocuments
from hope_documents.api.serializers.analyze import AnalysisJobStatusSerializer, AnalyzeInputSerializer
from hope_documents.models import AnalysisJob

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


class AnalyzeView(APIView):
    """Submit a document image for OCR analysis.

    Returns a job_id for async polling, or the full result when ?sync=true.
    """

    permission_classes = (CanAnalyzeDocuments,)
    serializer_class = AnalyzeInputSerializer

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
        )
        ext = pathlib.Path(image_file.name).suffix or ".png"
        job.image.save(f"{job.id}{ext}", image_file, save=True)
        job.queue()
        return Response({"job_id": str(job.id)}, status=status.HTTP_202_ACCEPTED)


class AnalyzeDetailView(APIView):
    """Retrieve the status and result of a previously submitted analysis job."""

    permission_classes = (CanAnalyzeDocuments,)

    def get(self, request: Request, job_id: Any, *args: Any, **kwargs: Any) -> Response:
        job = get_object_or_404(
            AnalysisJob.objects.select_related("document_type", "country"),
            pk=job_id,
        )
        return Response(AnalysisJobStatusSerializer(job).data)
