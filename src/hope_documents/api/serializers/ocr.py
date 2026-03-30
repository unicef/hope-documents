from rest_framework import serializers

from hope_ocr.ocr.engine import MatchMode, OcrEngineMode


class ExtractSerializer(serializers.Serializer):
    attachment = serializers.FileField()
    pattern = serializers.CharField(
        help_text="Pattern to search, if blank will perform analysis", default="", required=False
    )
    threshold = serializers.IntegerField(
        help_text="cv2 threshold [0..255]", default=128, required=False, min_value=0, max_value=255
    )
    mode = serializers.ChoiceField(
        help_text="Modality: Best, First, All", default=MatchMode.FIRST.name, choices=MatchMode.choices()
    )
    rotate = serializers.IntegerField(help_text="Rotate image", default=0, required=False)
    auto = serializers.BooleanField(help_text="Auto extract", default=False, required=False)
    number_only = serializers.BooleanField(help_text="Only extract numbers", default=False, required=False)
    psm = serializers.ChoiceField(
        choices=[(i, i) for i in range(14)],
        help_text="TS Page segmentation mode [0..13]",
        default=11,
        initial=11,
        required=False,
        allow_null=False,
    )
    oem = serializers.ChoiceField(
        choices=OcrEngineMode.choices(),
        help_text="TS OCR Engine mode [0..3]",
        default=OcrEngineMode.DEFAULT.value,
        initial=OcrEngineMode.DEFAULT.value,
        required=False,
        allow_null=False,
    )
