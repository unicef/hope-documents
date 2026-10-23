import base64
import binascii

from rest_framework import serializers

from hope_documents.models import AnalysisJob
from hope_ocr.archive.models import Country, DocumentType


class AnalyzeInputSerializer(serializers.Serializer):
    image_file = serializers.ImageField(required=False)
    image_url = serializers.URLField(required=False)
    image_base64 = serializers.CharField(required=False)
    document_type = serializers.CharField()
    country = serializers.CharField()
    callback_url = serializers.URLField(required=False, default="")

    def validate(self, data: dict) -> dict:
        provided = [k for k in ("image_file", "image_url", "image_base64") if data.get(k)]
        if len(provided) == 0:
            raise serializers.ValidationError("One of image_file, image_url, or image_base64 is required.")
        if len(provided) > 1:
            raise serializers.ValidationError("Only one of image_file, image_url, or image_base64 may be provided.")
        if data.get("image_base64"):
            raw = data["image_base64"]
            if "," in raw:
                raw = raw.split(",", 1)[1]
            try:
                base64.b64decode(raw, validate=True)
            except binascii.Error:
                raise serializers.ValidationError({"image_base64": "Invalid base64 encoding."}) from None
        try:
            data["document_type_obj"] = DocumentType.objects.get(code=data["document_type"])
        except DocumentType.DoesNotExist:
            raise serializers.ValidationError({"document_type": "No DocumentType with this code."}) from None
        try:
            data["country_obj"] = Country.objects.get(code2=data["country"])
        except Country.DoesNotExist:
            raise serializers.ValidationError({"country": "No Country with this code2."}) from None
        return data


class AnalysisJobStatusSerializer(serializers.ModelSerializer):
    job_id = serializers.UUIDField(source="id")
    document_type = serializers.CharField(source="document_type.code")
    country = serializers.CharField(source="country.code2")
    version = serializers.SerializerMethodField()
    version_matched = serializers.SerializerMethodField()
    attributes = serializers.SerializerMethodField()
    error = serializers.SerializerMethodField()

    class Meta:
        model = AnalysisJob
        fields = ["job_id", "status", "document_type", "country", "version", "version_matched", "attributes", "error"]

    def get_version(self, obj: AnalysisJob) -> str | None:
        if obj.status == AnalysisJob.Status.COMPLETED:
            return obj.matched_version or None
        return None

    def get_version_matched(self, obj: AnalysisJob) -> bool | None:
        if obj.status == AnalysisJob.Status.COMPLETED:
            return obj.version_matched
        return None

    def get_attributes(self, obj: AnalysisJob) -> list | None:
        if obj.status == AnalysisJob.Status.COMPLETED:
            return obj.result or []
        return None

    def get_error(self, obj: AnalysisJob) -> str | None:
        if obj.status == AnalysisJob.Status.FAILED:
            return obj.error
        return None
