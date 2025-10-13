from admin_extra_buttons.api import ExtraButtonsMixin, button
from django import forms
from django.contrib import admin, messages
from django.core.validators import MaxValueValidator, MinValueValidator
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.utils.module_loading import import_string

from ..ocr.engine import CV2Config, MatchMode, Processor, ScanEntryInfo, SearchInfo, TSConfig
from ..ocr.loaders import Loader, loader_registry
from ..utils.image import get_image_base64
from ..utils.language import fqn
from ..utils.timeit import time_it
from . import models

PSM_CHOICES = (
    (0, "(0) Orientation and script detection (OSD) only."),
    (1, "(1) Automatic page segmentation with OSD."),
    (2, "(2) Automatic page segmentation, but no OSD, or OCR."),
    (3, "(3) Fully automatic page segmentation, but no OSD. (Default)"),
    (4, "(4) Assume a single column of text of variable sizes."),
    (5, "(5) Assume a single uniform block of vertically aligned text."),
    (6, "(6) Assume a single uniform block of text."),
    (7, "(7) Treat the image as a single text line."),
    (8, "(8) Treat the image as a single word."),
    (9, "(9) Treat the image as a single word in a circle."),
    (10, "(10) Treat the image as a single character."),
    (11, "(11) Sparse text. Find as much text as possible in no particular order."),
    (12, "(12) Sparse text with OSD."),
    (13, "(13) Raw line. Treat the image as a single text line, bypassing hacks that are Tesseract-specific."),
)
OEM_CHOICES = (
    (0, "(0) Legacy engine only."),
    (1, "(1) Neural nets LSTM engine only."),
    (2, "(2) Legacy + LSTM engines."),
    (3, "(3) Default, based on what is available."),
)

LOADERS = [(fqn(p), p.__name__) for p in loader_registry]


class TestImageForm(forms.Form):
    image = forms.ImageField(validators=[])
    psm = forms.ChoiceField(initial=11, choices=PSM_CHOICES, help_text="Page segmentation modes")
    oem = forms.ChoiceField(initial=3, choices=OEM_CHOICES, help_text="OCR Engine modes")
    number_only = forms.BooleanField(initial=False, required=False, help_text="Only extract numbers")
    detect = forms.BooleanField(initial=False, required=False, help_text="Try to detect Document type")

    threshold = forms.IntegerField(initial=128, validators=[MinValueValidator(1), MaxValueValidator(255)])
    loaders = forms.MultipleChoiceField(choices=LOADERS, initial=[x[0] for x in LOADERS])

    target = forms.CharField(required=False, help_text="Text to search for in the document")
    max_errors = forms.IntegerField(
        initial=5, validators=[MinValueValidator(0)], help_text="Maximum number of errors allowed for a match"
    )
    mode = forms.TypedChoiceField(
        initial=MatchMode.FIRST.value,
        choices=MatchMode.choices(),
        coerce=lambda x: MatchMode(int(x)),
        help_text="Debug mode",
    )

    def clean_loaders(self) -> list[type[Loader]]:
        return [import_string(p) for p in self.cleaned_data["loaders"]]


@admin.register(models.Country)
class CountryAdmin(admin.ModelAdmin[models.Country]):
    list_display = ["name", "code2", "code3", "number"]
    search_fields = ["code2", "code3", "number", "name"]


@admin.register(models.DocumentType)
class DocumentTypeAdmin(admin.ModelAdmin[models.DocumentType]):
    list_display = ["code", "name"]
    search_fields = ["code", "name"]


@admin.register(models.DocumentRule)
class DocumentRuleAdmin(ExtraButtonsMixin, admin.ModelAdmin[models.DocumentRule]):
    list_display = ["country", "type"]
    search_fields = ["code", "name"]
    list_filter = ["country", "type"]
    autocomplete_fields = ["country", "type"]

    @button()  # type: ignore[arg-type]
    def scan_image(self, request: HttpRequest) -> HttpResponse:
        ctx = self.get_common_context(request)
        extractions: list[ScanEntryInfo]
        findings: list[SearchInfo]
        if request.method == "POST":
            form = TestImageForm(request.POST, request.FILES)
            if form.is_valid():
                with time_it() as m:
                    image_file = form.cleaned_data["image"]

                    ts_config = TSConfig(
                        psm=form.cleaned_data["psm"],
                        oem=form.cleaned_data["oem"],
                        number_only=form.cleaned_data["number_only"],
                    )
                    cv2_config = CV2Config(threshold=form.cleaned_data["threshold"])
                    p = Processor(ts_config=ts_config, cv2_config=cv2_config, loaders=form.cleaned_data["loaders"])
                    if form.cleaned_data["target"]:
                        findings = list(
                            p.find_text(
                                image_file,
                                form.cleaned_data["target"],
                                mode=form.cleaned_data["mode"],
                                max_errors=form.cleaned_data["max_errors"],
                            )
                        )
                        if text_found := any(x.found for x in findings):
                            self.message_user(request, "Text found")
                        else:
                            self.message_user(request, "Text not found", messages.WARNING)
                        ctx["text_found"] = text_found
                        ctx["searched_text"] = form.cleaned_data["target"]
                        ctx["results"] = findings
                    else:
                        self.message_user(request, "Document processed")
                        extractions = list(p.process(image_file))
                        ctx["results"] = extractions

                ctx["total_time"] = m

                ctx["infos"] = {"filename": image_file, "config": ts_config}
                ctx["image_src"] = get_image_base64(image_file)
        else:
            form = TestImageForm()
        ctx["form"] = form
        return render(request, "hope_documents/test_image.html", ctx)
