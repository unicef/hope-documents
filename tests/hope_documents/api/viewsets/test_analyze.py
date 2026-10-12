import base64
import io
import uuid
from unittest.mock import MagicMock, patch

import pytest
from django.core.files.base import ContentFile
from django.urls import reverse
from PIL import Image as PILImage
from rest_framework import status
from rest_framework.test import APIClient

from factories.analysis import AnalysisJobFactory
from factories.documents import AttributeFactory, CountryFactory, DocumentAttributeFactory, DocumentFactory, DocumentTypeFactory
from hope_documents.models import AnalysisJob
from hope_ocr.archive.models import Attribute


def make_png_bytes() -> bytes:
    buf = io.BytesIO()
    PILImage.new("RGB", (50, 20), color="white").save(buf, "PNG")
    buf.seek(0)
    return buf.read()


@pytest.fixture
def png_bytes():
    return make_png_bytes()


@pytest.fixture
def document_type(db):
    return DocumentTypeFactory(code="PAS", name="Passport")


@pytest.fixture
def country(db):
    return CountryFactory(code2="IT", code3="ITA", number="380", name="Italy")


@pytest.mark.django_db
def test_upload_multipart_file(app, png_bytes, document_type, country):
    url = reverse("api:analyze-create")
    with patch("hope_documents.api.viewsets.analyze.process_analysis_job") as mock_task:
        response = app.post(
            url,
            params={"document_type": document_type.code, "country": country.code2},
            upload_files=[("image_file", "passport.png", png_bytes)],
        )
    assert response.status_code == status.HTTP_202_ACCEPTED
    assert "job_id" in response.json
    mock_task.delay.assert_called_once()
    job = AnalysisJob.objects.get(pk=response.json["job_id"])
    assert job.document_type == document_type
    assert job.country == country
    assert job.status == AnalysisJob.Status.PENDING


@pytest.mark.django_db
def test_upload_url(app, png_bytes, document_type, country, mocked_responses):
    mocked_responses.add(mocked_responses.GET, "https://example.com/passport.png", body=png_bytes, status=200)
    url = reverse("api:analyze-create")
    with patch("hope_documents.api.viewsets.analyze.process_analysis_job"):
        response = app.post(
            url,
            params={
                "document_type": document_type.code,
                "country": country.code2,
                "image_url": "https://example.com/passport.png",
            },
        )
    assert response.status_code == status.HTTP_202_ACCEPTED
    assert "job_id" in response.json


@pytest.mark.django_db
def test_upload_base64(app, png_bytes, document_type, country):
    b64 = base64.b64encode(png_bytes).decode()
    url = reverse("api:analyze-create")
    with patch("hope_documents.api.viewsets.analyze.process_analysis_job"):
        response = app.post(
            url,
            params={
                "document_type": document_type.code,
                "country": country.code2,
                "image_base64": b64,
            },
        )
    assert response.status_code == status.HTTP_202_ACCEPTED
    assert "job_id" in response.json


@pytest.mark.django_db
def test_upload_missing_image(app, document_type, country):
    url = reverse("api:analyze-create")
    response = app.post(
        url,
        params={"document_type": document_type.code, "country": country.code2},
        expect_errors=True,
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_upload_multiple_image_sources_rejected(app, png_bytes, document_type, country):
    b64 = base64.b64encode(png_bytes).decode()
    url = reverse("api:analyze-create")
    response = app.post(
        url,
        params={
            "document_type": document_type.code,
            "country": country.code2,
            "image_base64": b64,
            "image_url": "https://example.com/x.png",
        },
        expect_errors=True,
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_upload_invalid_document_type(app, png_bytes, country):
    b64 = base64.b64encode(png_bytes).decode()
    url = reverse("api:analyze-create")
    response = app.post(
        url,
        params={"document_type": "ZZZ", "country": country.code2, "image_base64": b64},
        expect_errors=True,
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_upload_invalid_country(app, png_bytes, document_type):
    b64 = base64.b64encode(png_bytes).decode()
    url = reverse("api:analyze-create")
    response = app.post(
        url,
        params={"document_type": document_type.code, "country": "ZZ", "image_base64": b64},
        expect_errors=True,
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_upload_unauthenticated(png_bytes, document_type, country):
    client = APIClient()
    b64 = base64.b64encode(png_bytes).decode()
    url = reverse("api:analyze-create")
    response = client.post(url, {"document_type": document_type.code, "country": country.code2, "image_base64": b64})
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
def test_upload_with_callback_url(app, png_bytes, document_type, country):
    b64 = base64.b64encode(png_bytes).decode()
    url = reverse("api:analyze-create")
    with patch("hope_documents.api.viewsets.analyze.process_analysis_job"):
        response = app.post(
            url,
            params={
                "document_type": document_type.code,
                "country": country.code2,
                "image_base64": b64,
                "callback_url": "https://example.com/callback",
            },
        )
    assert response.status_code == status.HTTP_202_ACCEPTED
    job = AnalysisJob.objects.get(pk=response.json["job_id"])
    assert job.callback_url == "https://example.com/callback"


@pytest.mark.django_db
def test_detail_pending(app, document_type, country):
    job = AnalysisJobFactory(document_type=document_type, country=country, status=AnalysisJob.Status.PENDING)
    url = reverse("api:analyze-detail", kwargs={"job_id": str(job.id)})
    response = app.get(url)
    assert response.status_code == status.HTTP_200_OK
    data = response.json
    assert data["status"] == "pending"
    assert data["job_id"] == str(job.id)
    assert data["document_type"] == document_type.code
    assert data["country"] == country.code2
    assert data["version"] is None
    assert data["attributes"] is None


@pytest.mark.django_db
def test_detail_running(app, document_type, country):
    job = AnalysisJobFactory(document_type=document_type, country=country, status=AnalysisJob.Status.RUNNING)
    url = reverse("api:analyze-detail", kwargs={"job_id": str(job.id)})
    response = app.get(url)
    assert response.status_code == status.HTTP_200_OK
    assert response.json["status"] == "running"
    assert response.json["version"] is None
    assert response.json["attributes"] is None


@pytest.mark.django_db
def test_detail_completed_with_version_match(app, document_type, country):
    job = AnalysisJobFactory(
        document_type=document_type,
        country=country,
        status=AnalysisJob.Status.COMPLETED,
        matched_version="v1",
        version_matched=True,
        result=[
            {"attribute_name": "first_name", "extracted_value": "John"},
            {"attribute_name": "last_name", "extracted_value": "Doe"},
        ],
    )
    url = reverse("api:analyze-detail", kwargs={"job_id": str(job.id)})
    response = app.get(url)
    assert response.status_code == status.HTTP_200_OK
    data = response.json
    assert data["status"] == "completed"
    assert data["version"] == "v1"
    assert data["version_matched"] is True
    assert len(data["attributes"]) == 2
    assert data["attributes"][0]["attribute_name"] == "first_name"
    assert data["error"] is None


@pytest.mark.django_db
def test_detail_completed_no_version_match(app, document_type, country):
    job = AnalysisJobFactory(
        document_type=document_type,
        country=country,
        status=AnalysisJob.Status.COMPLETED,
        matched_version="",
        version_matched=False,
        result=[
            {"attribute_name": "first_name", "extracted_value": "John"},
            {"attribute_name": "last_name", "extracted_value": ""},
            {"attribute_name": "number", "extracted_value": "AB123"},
        ],
    )
    url = reverse("api:analyze-detail", kwargs={"job_id": str(job.id)})
    response = app.get(url)
    assert response.status_code == status.HTTP_200_OK
    data = response.json
    assert data["version"] is None
    assert data["version_matched"] is False
    assert len(data["attributes"]) == 3


@pytest.mark.django_db
def test_detail_failed(app, document_type, country):
    job = AnalysisJobFactory(
        document_type=document_type,
        country=country,
        status=AnalysisJob.Status.FAILED,
        error="Tesseract not found",
    )
    url = reverse("api:analyze-detail", kwargs={"job_id": str(job.id)})
    response = app.get(url)
    assert response.status_code == status.HTTP_200_OK
    data = response.json
    assert data["status"] == "failed"
    assert data["error"] == "Tesseract not found"
    assert data["attributes"] is None


@pytest.mark.django_db
def test_detail_not_found(app):
    url = reverse("api:analyze-detail", kwargs={"job_id": str(uuid.uuid4())})
    response = app.get(url, expect_errors=True)
    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
def test_detail_unauthenticated(document_type, country):
    client = APIClient()
    job = AnalysisJobFactory(document_type=document_type, country=country)
    url = reverse("api:analyze-detail", kwargs={"job_id": str(job.id)})
    response = client.get(url)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def _create_job_with_image(document_type, country, png_bytes, **kwargs):
    job = AnalysisJobFactory.build(document_type=document_type, country=country, **kwargs)
    job.save()
    job.image.save(f"{job.id}.png", ContentFile(png_bytes), save=True)
    return job


@pytest.mark.django_db
def test_task_generic_fallback_no_documents(document_type, country, png_bytes):
    """When no Document versions are configured, task falls back to system attributes."""
    from hope_documents.tasks import process_analysis_job

    job = _create_job_with_image(document_type, country, png_bytes)

    with patch("hope_ocr.ocr.engine.Processor") as MockProc:
        MockProc.return_value.find_single.return_value = ("John", MagicMock())
        process_analysis_job(str(job.id))

    job.refresh_from_db()
    assert job.status == AnalysisJob.Status.COMPLETED
    assert job.version_matched is False
    assert job.matched_version == ""
    assert job.result is not None
    system_names = {a["attribute_name"] for a in job.result}
    # Should include system attributes (first_name, last_name, number seeded by migration)
    assert len(system_names) > 0


@pytest.mark.django_db
def test_task_version_matched(document_type, country, png_bytes):
    """When a version yields extracted values, it is selected and version_matched=True."""
    from hope_documents.tasks import process_analysis_job

    attr = Attribute.objects.get(name="first_name")
    doc = DocumentFactory(document_type=document_type, country=country, version="v1")
    DocumentAttributeFactory(document=doc, attribute=attr)

    job = _create_job_with_image(document_type, country, png_bytes)

    with patch("hope_ocr.ocr.engine.Processor") as MockProc:
        MockProc.return_value.find_single.return_value = ("John", MagicMock())
        process_analysis_job(str(job.id))

    job.refresh_from_db()
    assert job.status == AnalysisJob.Status.COMPLETED
    assert job.version_matched is True
    assert job.matched_version == "v1"
    assert any(a["attribute_name"] == "first_name" for a in job.result)


@pytest.mark.django_db
def test_task_version_no_score_falls_back(document_type, country, png_bytes):
    """When a version exists but extraction yields nothing, falls back to generic."""
    from hope_documents.tasks import process_analysis_job

    attr = AttributeFactory(name="custom_field")
    doc = DocumentFactory(document_type=document_type, country=country, version="v2")
    DocumentAttributeFactory(document=doc, attribute=attr)

    job = _create_job_with_image(document_type, country, png_bytes)

    with patch("hope_ocr.ocr.engine.Processor") as MockProc:
        # All extraction returns empty string
        MockProc.return_value.find_single.return_value = ("", None)
        process_analysis_job(str(job.id))

    job.refresh_from_db()
    assert job.status == AnalysisJob.Status.COMPLETED
    assert job.version_matched is False


@pytest.mark.django_db
def test_task_handles_exception(document_type, country, png_bytes):
    """On unexpected error the job is marked FAILED and error is stored."""
    from hope_documents.tasks import process_analysis_job

    job = _create_job_with_image(document_type, country, png_bytes)

    with patch("hope_ocr.ocr.engine.Processor", side_effect=RuntimeError("boom")):
        with pytest.raises(RuntimeError):
            process_analysis_job(str(job.id))

    job.refresh_from_db()
    assert job.status == AnalysisJob.Status.FAILED
    assert "boom" in job.error


@pytest.mark.django_db
def test_task_fires_callback(document_type, country, png_bytes, mocked_responses):
    """When callback_url is set the task POSTs results on completion."""
    from hope_documents.tasks import process_analysis_job

    mocked_responses.add(mocked_responses.POST, "https://example.com/hook", status=200)
    job = _create_job_with_image(document_type, country, png_bytes, callback_url="https://example.com/hook")

    with patch("hope_ocr.ocr.engine.Processor") as MockProc:
        MockProc.return_value.find_single.return_value = ("", None)
        process_analysis_job(str(job.id))

    assert len(mocked_responses.calls) == 1
    job.refresh_from_db()
    assert job.status == AnalysisJob.Status.COMPLETED


@pytest.mark.django_db
def test_task_no_callback_when_url_empty(document_type, country, png_bytes, mocked_responses):
    """When no callback_url is set no HTTP call is made."""
    from hope_documents.tasks import process_analysis_job

    job = _create_job_with_image(document_type, country, png_bytes, callback_url="")

    with patch("hope_ocr.ocr.engine.Processor") as MockProc:
        MockProc.return_value.find_single.return_value = ("", None)
        process_analysis_job(str(job.id))

    assert len(mocked_responses.calls) == 0
    job.refresh_from_db()
    assert job.status == AnalysisJob.Status.COMPLETED
