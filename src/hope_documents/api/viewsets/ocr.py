import os
from typing import Any
from PIL.ExifTags import TAGS
from PIL import Image
from humanize import naturalsize
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from hope_ocr.ocr.engine import CV2Config, Processor, TSConfig, MatchMode
from hope_documents.api.serializers.ocr import InspectSerializer, ExtractSerializer
from hope_ocr.utils._timeit import time_it
from hope_ocr.utils.image import get_image_base64


class OCRView(APIView):
    permission_classes = (IsAuthenticated,)

    @classmethod
    def _set_params(cls, serializer):
        params = dict()
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

    def post(self, request, *args, **kwargs):
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
        except Exception:
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


class InspectView(APIView):
    serializer_class = InspectSerializer

#     def post(self, request, *args, **kwargs):
#         serializer = self.serializer_class(data=request.data)
#
#         # pattern, found, distance = expected_args
#
#         if not serializer.is_valid():
#             return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
#
#         uploaded_file = serializer.validated_data["attachment"]
#
#         filename = uploaded_file.name
#         name, extension = os.path.splitext(filename)
#         ser_data = serializer.validated_data
#
#         data = {"filename": uploaded_file.name, "extension": extension.lstrip("."), "params": {}, "findings": []}
#         try:
#             image = Image.open(uploaded_file.name)
#             width, height = image.size
#             data["dimensions"] = {
#                 "width": width,
#                 "height": height,
#             }
#         except Exception:
#             data["dimensions"] = None  # Not an image
#
#         self._set_params(serializer)
#
#         with time_it() as m:
#             processor = Processor(ts_config=TSConfig(), cv2_config=CV2Config())
#             image_info: dict[str, Any] = {}
#             image_info["size"] = naturalsize(image.stat().st_size, False, True, "%.3f")
#             image_info["dim"] = original.size
#             exifdata = original.getexif()
#             for tag_id in exifdata:
#                 tag = str(TAGS.get(tag_id, tag_id))
#                 value = exifdata.get(tag_id)
#                 if isinstance(value, bytes):
#                     value = value.decode(errors="ignore")
#                 image_info[tag] = str(value)
#
#             for loader in processor.loaders:
#                 for image, angle in loader.rotate(original):
#                     # if expected_args and pattern:
#                     text, match = processor.find_single(image, pattern)
#                     # else:
#                     #     text = ""
#                     #     match = None
#                     data.append(
#                         {
#                             "loader": loader.__class__.__name__,
#                             "angle": angle,
#                             "match": match,
#                             "pattern": pattern,
#                             "image": get_image_base64(image),
#                             "text": text,
#                         }
#                     )
#         data = {
#             # "filename": file_label,
#             "data": data,
#             "timing": m,
#             "mode": mode,
#             "original": get_image_base64(original),
#             "image_info": image_info,
#         }
#
#         # "inspect.html"
#
#         # ts_config = TSConfig(oem=ser_data["oem"], psm=ser_data["psm"], number_only=ser_data["number_only"])
#         # p = Processor(ts_config=ts_config, cv2_config=CV2Config(threshold=ser_data["threshold"]))
#         # if pattern := ser_data.get("pattern"):
#         #     data["findings"] = [
#         #         {
#         #             "angle": finding.angle,
#         #             "attempts": finding.attempts,
#         #             "error": finding.error,
#         #             "found": finding.found,
#         #             "match": [finding.match.text, finding.match.distance],
#         #             "psm": finding.psm,
#         #             "text": finding.text,
#         #             "time": finding.time,
#         #         }
#         #         for finding in list(
#         #             p.find_text(image, pattern, mode=MatchMode(ser_data["mode"]), rotations=[ser_data["rotate"]])
#         #         )
#         #     ]
#         #
#         # else:
#         #     for extracted in p.process(uploaded_file, rotate=ser_data["rotate"]):
#         #         data[extracted.loader] = {
#         #             "text": extracted.text,
#         #             "error": extracted.error,
#         #             "time": extracted.time,
#         #         }
#         return Response(data, status=status.HTTP_200_OK)
