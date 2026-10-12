import base64
from typing import Any

import requests as http_client
from django.core.files.base import ContentFile
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from hope_documents.api.serializers.analyze import AnalysisJobStatusSerializer, AnalyzeInputSerializer
from hope_documents.models import AnalysisJob
from hope_documents.tasks import process_analysis_job


def _resolve_image(data: dict) -> Any:
    if data.get("image_file"):
        return data["image_file"]
    if data.get("image_url"):
        try:
            resp = http_client.get(data["image_url"], timeout=10)
            resp.raise_for_status()
            return ContentFile(resp.content, name="url_image.png")
        except Exception:
            return None
    if data.get("image_base64"):
        raw = data["image_base64"]
        if "," in raw:
            raw = raw.split(",", 1)[1]
        content = base64.b64decode(raw)
        return ContentFile(content, name="base64_image.png")
    return None


class AnalyzeView(APIView):
    permission_classes = (IsAuthenticated,)
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
        job.image.save(f"{job.id}.png", image_file, save=True)
        process_analysis_job.delay(str(job.id))
        return Response({"job_id": str(job.id)}, status=status.HTTP_202_ACCEPTED)


class AnalyzeDetailView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request: Request, job_id: Any, *args: Any, **kwargs: Any) -> Response:
        job = get_object_or_404(
            AnalysisJob.objects.select_related("document_type", "country"),
            pk=job_id,
        )
        return Response(AnalysisJobStatusSerializer(job).data)
