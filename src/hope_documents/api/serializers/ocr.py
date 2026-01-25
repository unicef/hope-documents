from rest_framework import serializers

from hope_ocr.ocr.engine import MatchMode


class ExtractSerializer(serializers.Serializer):
    attachment = serializers.FileField()
    pattern = serializers.CharField(
        help_text="Pattern to search, if blank will perform analysis", default="", required=False
    )
    threshold = serializers.IntegerField(help_text="cv2 threshold [0..255]", default=128, required=False)
    mode = serializers.ChoiceField(
        help_text="cv2 threshold [0..255]", default=MatchMode.FIRST.name, choices=MatchMode.choices()
    )
    rotate = serializers.IntegerField(help_text="Rotate image", default=0, required=False)
    auto = serializers.BooleanField(help_text="Auto extract", default=False, required=False)
    number_only = serializers.BooleanField(help_text="Only extract numbers", default=False, required=False)
    psm = serializers.IntegerField(help_text="TS Page segmentation mode [0..13]", default=11, required=False)
    oem = serializers.IntegerField(help_text="TS OCR Engine mode [0..3]", default=3, required=False)


class InspectSerializer(serializers.Serializer):
    attachment = serializers.FileField()
    mode = serializers.ChoiceField(
        help_text="cv2 threshold [0..255]", default=MatchMode.FIRST.name, choices=MatchMode.choices()
    )
