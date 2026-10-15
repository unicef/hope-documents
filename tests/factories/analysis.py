import io

import factory
from PIL import Image as PILImage
from django.core.files.base import ContentFile

from factories.base import AutoRegisterModelFactory
from factories.documents import CountryFactory, DocumentTypeFactory
from hope_documents.models import AnalysisJob


def _make_png_bytes() -> bytes:
    buf = io.BytesIO()
    PILImage.new("RGB", (10, 10), color="white").save(buf, "PNG")
    buf.seek(0)
    return buf.read()


class AnalysisJobFactory(AutoRegisterModelFactory):
    class Meta:
        model = AnalysisJob

    document_type = factory.SubFactory(DocumentTypeFactory)
    country = factory.SubFactory(CountryFactory)
    status = AnalysisJob.Status.PENDING
    validation_mode = AnalysisJob.ValidationMode.FALL_BACK_TO_BEST_MATCH
    callback_url = ""
    matched_version = ""
    version_matched = None
    result = None
    error = ""

    @factory.post_generation
    def image(self: AnalysisJob, create: bool, extracted: object, **kwargs: object) -> None:
        if extracted:
            self.image = extracted
        else:
            self.image.save(f"{self.id}.png", ContentFile(_make_png_bytes()), save=False)
        if create:
            self.save()
