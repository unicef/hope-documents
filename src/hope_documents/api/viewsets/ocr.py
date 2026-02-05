import os
from typing import Any

from PIL import Image
from rest_framework import request, serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from hope_documents.api.serializers.ocr import ExtractSerializer
from hope_ocr.ocr.engine import CV2Config, MatchMode, Processor, TSConfig


class OCRView(APIView):
    permission_classes = (IsAuthenticated,)

    @classmethod
    def _set_params(cls, serializer: serializers.Serializer) -> dict[str, Any]:
        params: dict[str, Any] = {}
        for field_name, field in serializer.fields.items():
            if field_name != "attachment":
                passed = field_name in serializer.initial_data
                value = serializer.validated_data.get(field_name, field.default)

                params[field_name] = {
                    "value": value,
                    "passed": passed,
                    "default": field.default,
                }
        return params


class ExtractView(OCRView):
    serializer_class = ExtractSerializer

    def post(self, request: request.Request, *args: Any, **kwargs: Any) -> Response:
        serializer = self.serializer_class(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        uploaded_file = serializer.validated_data["attachment"]

        filename = uploaded_file.name
        name, extension = os.path.splitext(filename)
        ser_data = serializer.validated_data

        data = {}
        try:
            image = Image.open(uploaded_file)
            width, height = image.size
            data["info"] = {
                "filename": uploaded_file.name,
                "extension": extension.lstrip("."),
                "width": width,
                "height": height,
            }
        except (OSError, Image.UnidentifiedImageError):
            data["file"] = None  # Not an image

        ts_config = TSConfig(oem=ser_data["oem"], psm=ser_data["psm"], number_only=ser_data["number_only"])
        p = Processor(ts_config=ts_config, cv2_config=CV2Config(threshold=ser_data["threshold"]))
        if pattern := ser_data.get("pattern"):
            data["findings"] = [
                {
                    "angle": finding.angle,
                    "attempts": finding.attempts,
                    "error": finding.error,
                    "found": finding.found,
                    "match": [finding.match.text, finding.match.distance],
                    "psm": finding.psm,
                    "text": finding.text,
                    "time": finding.time,
                }
                for finding in list(
                    p.find_text(image, pattern, mode=MatchMode(ser_data["mode"]), rotations=[ser_data["rotate"]])
                )
            ]

        else:
            data["loaders"] = {}
            for extracted in p.process(uploaded_file, rotate=ser_data["rotate"]):
                data["loaders"][extracted.loader] = {
                    "text": extracted.text,
                    "error": extracted.error,
                    "time": extracted.time,
                }
        data["params"] = self._set_params(serializer)
        return Response(data, status=status.HTTP_200_OK)

