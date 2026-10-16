import base64
import io
import uuid
from unittest.mock import MagicMock, patch

import pytest
import requests
from PIL import Image as PILImage
from django.core.files.base import ContentFile
from django.urls import reverse
from factories.analysis import AnalysisJobFactory
from factories.documents import (
    AttributeFactory,
    CountryFactory,
    DocumentAttributeFactory,
    DocumentFactory,
    DocumentTypeFactory,
)
from rest_framework import status
from rest_framework.test import APIClient

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
    assert data["version_matched"] is None
    assert data["attributes"] is None


@pytest.mark.django_db
def test_detail_running(app, document_type, country):
    job = AnalysisJobFactory(document_type=document_type, country=country, status=AnalysisJob.Status.RUNNING)
    url = reverse("api:analyze-detail", kwargs={"job_id": str(job.id)})
    response = app.get(url)
    assert response.status_code == status.HTTP_200_OK
    assert response.json["status"] == "running"
    assert response.json["version"] is None
    assert response.json["version_matched"] is None
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
            {"attribute_name": "document_number", "extracted_value": "AB123"},
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

    with patch("hope_documents.tasks.Processor") as mock_proc:
        mock_proc.return_value.find_single.return_value = ("John", MagicMock())
        process_analysis_job(str(job.id))

    job.refresh_from_db()
    assert job.status == AnalysisJob.Status.COMPLETED
    assert job.version_matched is False
    assert job.matched_version == ""
    assert job.result is not None
    system_names = {a["attribute_name"] for a in job.result}
    assert system_names == {"first_name", "last_name", "document_number"}


@pytest.mark.django_db
def test_task_version_matched(document_type, country, png_bytes):
    """When a version yields extracted values, it is selected and version_matched=True."""
    from hope_documents.tasks import process_analysis_job

    attr = Attribute.objects.get(name="first_name")
    doc = DocumentFactory(document_type=document_type, country=country, version="v1")
    DocumentAttributeFactory(document=doc, attribute=attr)

    job = _create_job_with_image(document_type, country, png_bytes)

    with patch("hope_documents.tasks.Processor") as mock_proc:
        mock_proc.return_value.find_single.return_value = ("John", MagicMock())
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

    with patch("hope_documents.tasks.Processor") as mock_proc:
        # All extraction returns empty string
        mock_proc.return_value.find_single.return_value = ("", None)
        process_analysis_job(str(job.id))

    job.refresh_from_db()
    assert job.status == AnalysisJob.Status.COMPLETED
    assert job.version_matched is False


@pytest.mark.django_db
def test_task_handles_exception(document_type, country, png_bytes):
    """On unexpected error the job is marked FAILED and error is stored."""
    from hope_documents.tasks import process_analysis_job

    job = _create_job_with_image(document_type, country, png_bytes)

    with patch("hope_documents.tasks.Processor", side_effect=RuntimeError("boom")):
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

    with patch("hope_documents.tasks.Processor") as mock_proc:
        mock_proc.return_value.find_single.return_value = ("", None)
        process_analysis_job(str(job.id))

    assert len(mocked_responses.calls) == 1
    job.refresh_from_db()
    assert job.status == AnalysisJob.Status.COMPLETED


@pytest.mark.django_db
def test_task_no_callback_when_url_empty(document_type, country, png_bytes, mocked_responses):
    """When no callback_url is set no HTTP call is made."""
    from hope_documents.tasks import process_analysis_job

    job = _create_job_with_image(document_type, country, png_bytes, callback_url="")

    with patch("hope_documents.tasks.Processor") as mock_proc:
        mock_proc.return_value.find_single.return_value = ("", None)
        process_analysis_job(str(job.id))

    assert len(mocked_responses.calls) == 0
    job.refresh_from_db()
    assert job.status == AnalysisJob.Status.COMPLETED


@pytest.mark.django_db
def test_upload_invalid_base64(app, document_type, country):
    url = reverse("api:analyze-create")
    response = app.post(
        url,
        params={
            "document_type": document_type.code,
            "country": country.code2,
            "image_base64": "not-valid-base64!!!",
        },
        expect_errors=True,
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "image_base64" in response.json


@pytest.mark.django_db
def test_upload_base64_data_uri_prefix(app, png_bytes, document_type, country):
    """base64 supplied as a full data-URI (data:image/png;base64,...) is accepted."""
    b64 = "data:image/png;base64," + base64.b64encode(png_bytes).decode()
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


@pytest.mark.django_db
def test_upload_url_fetch_failure(app, document_type, country, mocked_responses):
    mocked_responses.add(mocked_responses.GET, "https://example.com/bad.png", status=404)
    url = reverse("api:analyze-create")
    response = app.post(
        url,
        params={
            "document_type": document_type.code,
            "country": country.code2,
            "image_url": "https://example.com/bad.png",
        },
        expect_errors=True,
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_task_callback_failure_does_not_fail_job(document_type, country, png_bytes):
    """A failed callback POST is logged and swallowed — the job still completes."""
    from hope_documents.tasks import process_analysis_job

    job = _create_job_with_image(document_type, country, png_bytes, callback_url="https://example.com/hook")

    with patch("hope_documents.tasks.Processor") as mock_proc:
        mock_proc.return_value.find_single.return_value = ("", None)
        with patch("requests.post", side_effect=requests.RequestException("network error")):
            process_analysis_job(str(job.id))

    job.refresh_from_db()
    assert job.status == AnalysisJob.Status.COMPLETED


def test_resolve_image_returns_none_for_empty_data():
    """_resolve_image returns None when no image key is present in data."""
    from hope_documents.api.viewsets.analyze import _resolve_image

    assert _resolve_image({}) is None


def test_resolve_image_base64_prefix_without_colon():
    """_resolve_image handles a data-URI-style prefix that contains no colon."""
    import base64 as _base64

    from hope_documents.api.viewsets.analyze import _resolve_image

    raw = b"\x89PNG\r\n"
    payload = "nocoronprefix," + _base64.b64encode(raw).decode()
    result = _resolve_image({"image_base64": payload})
    assert result is not None


def test_analysis_job_str(document_type, country):
    job = AnalysisJobFactory(document_type=document_type, country=country)
    assert str(job) == f"AnalysisJob({job.id}, {job.status})"


@pytest.mark.django_db
def test_task_lower_scoring_document_does_not_replace_best(document_type, country, png_bytes):
    """When a second document scores lower it does not replace the best version."""
    from hope_documents.tasks import process_analysis_job

    attr = Attribute.objects.get(name="first_name")
    doc1 = DocumentFactory(document_type=document_type, country=country, version="v1")
    DocumentAttributeFactory(document=doc1, attribute=attr)
    doc2 = DocumentFactory(document_type=document_type, country=country, version="v2")
    DocumentAttributeFactory(document=doc2, attribute=AttributeFactory(name="rare_field"))

    job = _create_job_with_image(document_type, country, png_bytes)

    def _side_effect(image, name):
        return ("John", MagicMock()) if name == "first_name" else ("", None)

    with patch("hope_documents.tasks.Processor") as mock_proc:
        mock_proc.return_value.find_single.side_effect = _side_effect
        process_analysis_job(str(job.id))

    job.refresh_from_db()
    assert job.version_matched is True
    assert job.matched_version == "v1"


@pytest.mark.django_db
def test_validation_mode_not_in_request_defaults_to_fall_back_to_best_match(app, png_bytes, document_type, country):
    url = reverse("api:analyze-create")
    with patch("hope_documents.api.viewsets.analyze.process_analysis_job"):
        response = app.post(
            url,
            params={"document_type": document_type.code, "country": country.code2},
            upload_files=[("image_file", "passport.png", png_bytes)],
        )
    assert response.status_code == status.HTTP_202_ACCEPTED
    job = AnalysisJob.objects.get(pk=response.json["job_id"])
    assert job.validation_mode == AnalysisJob.ValidationMode.FALL_BACK_TO_BEST_MATCH


@pytest.mark.django_db
def test_serializer_rejects_invalid_validation_mode(app, png_bytes, document_type, country):
    url = reverse("api:analyze-create")
    response = app.post(
        url,
        params={
            "document_type": document_type.code,
            "country": country.code2,
            "image_base64": base64.b64encode(png_bytes).decode(),
            "validation_mode": "bad_value",
        },
        expect_errors=True,
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_status_response_includes_validation_mode(app, document_type, country):
    job = AnalysisJobFactory(
        document_type=document_type,
        country=country,
        status=AnalysisJob.Status.PENDING,
        validation_mode=AnalysisJob.ValidationMode.KEEP_VALUE_MARK_INVALID,
    )
    url = reverse("api:analyze-detail", kwargs={"job_id": str(job.id)})
    response = app.get(url)
    assert response.status_code == status.HTTP_200_OK
    assert "validation_mode" in response.json
    assert response.json["validation_mode"] == AnalysisJob.ValidationMode.KEEP_VALUE_MARK_INVALID


@pytest.mark.django_db
def test_task_fall_back_to_best_match_no_is_valid_key(document_type, country, png_bytes):
    """FALL_BACK_TO_BEST_MATCH: invalid value is included as-is with no is_valid flag."""
    from hope_documents.tasks import process_analysis_job

    attr = Attribute.objects.get(name="first_name")
    doc = DocumentFactory(document_type=document_type, country=country, version="v1")
    DocumentAttributeFactory(document=doc, attribute=attr, validation_expression=r"\d{9}")

    job = _create_job_with_image(
        document_type, country, png_bytes, validation_mode=AnalysisJob.ValidationMode.FALL_BACK_TO_BEST_MATCH
    )

    with patch("hope_documents.tasks.Processor") as mock_proc:
        mock_proc.return_value.find_single.return_value = ("JOHN", MagicMock())
        process_analysis_job(str(job.id))

    job.refresh_from_db()
    assert job.status == AnalysisJob.Status.COMPLETED
    assert all("is_valid" not in a for a in job.result)


@pytest.mark.django_db
def test_task_fall_back_to_best_match_invalid_value_reduces_score(document_type, country, png_bytes):
    """FALL_BACK_TO_BEST_MATCH: non-conforming values don't count toward score; if no version
    scores > 0 the generic fallback is returned instead of any configured version."""
    from hope_documents.tasks import process_analysis_job

    attr = Attribute.objects.get(name="first_name")
    doc = DocumentFactory(document_type=document_type, country=country, version="v1")
    DocumentAttributeFactory(document=doc, attribute=attr, validation_expression=r"\d{9}")

    job = _create_job_with_image(
        document_type, country, png_bytes, validation_mode=AnalysisJob.ValidationMode.FALL_BACK_TO_BEST_MATCH
    )

    with patch("hope_documents.tasks.Processor") as mock_proc:
        # All extracted values fail validation → score stays 0 → generic fallback
        mock_proc.return_value.find_single.return_value = ("JOHN", MagicMock())
        process_analysis_job(str(job.id))

    job.refresh_from_db()
    assert job.status == AnalysisJob.Status.COMPLETED
    assert job.version_matched is False
    system_names = {a["attribute_name"] for a in job.result}
    assert system_names == {"first_name", "last_name", "document_number"}


@pytest.mark.django_db
def test_task_keep_value_mark_invalid_valid_value(document_type, country, png_bytes):
    """KEEP_VALUE_MARK_INVALID: value matching the expression gets is_valid=True."""
    from hope_documents.tasks import process_analysis_job

    attr = Attribute.objects.get(name="first_name")
    doc = DocumentFactory(document_type=document_type, country=country, version="v1")
    DocumentAttributeFactory(document=doc, attribute=attr, validation_expression=r"\d{9}")

    job = _create_job_with_image(
        document_type, country, png_bytes, validation_mode=AnalysisJob.ValidationMode.KEEP_VALUE_MARK_INVALID
    )

    with patch("hope_documents.tasks.Processor") as mock_proc:
        mock_proc.return_value.find_single.return_value = ("123456789", MagicMock())
        process_analysis_job(str(job.id))

    job.refresh_from_db()
    assert job.status == AnalysisJob.Status.COMPLETED
    first_name_result = next(a for a in job.result if a["attribute_name"] == "first_name")
    assert first_name_result["is_valid"] is True
    assert first_name_result["extracted_value"] == "123456789"


@pytest.mark.django_db
def test_task_keep_value_mark_invalid_invalid_value(document_type, country, png_bytes):
    """KEEP_VALUE_MARK_INVALID: value not matching the expression gets is_valid=False; job completes."""
    from hope_documents.tasks import process_analysis_job

    attr = Attribute.objects.get(name="first_name")
    doc = DocumentFactory(document_type=document_type, country=country, version="v1")
    DocumentAttributeFactory(document=doc, attribute=attr, validation_expression=r"\d{9}")

    job = _create_job_with_image(
        document_type, country, png_bytes, validation_mode=AnalysisJob.ValidationMode.KEEP_VALUE_MARK_INVALID
    )

    with patch("hope_documents.tasks.Processor") as mock_proc:
        mock_proc.return_value.find_single.return_value = ("JOHN", MagicMock())
        process_analysis_job(str(job.id))

    job.refresh_from_db()
    assert job.status == AnalysisJob.Status.COMPLETED
    first_name_result = next(a for a in job.result if a["attribute_name"] == "first_name")
    assert first_name_result["is_valid"] is False
    assert first_name_result["extracted_value"] == "JOHN"


@pytest.mark.django_db
def test_task_treat_as_not_found_invalid(document_type, country, png_bytes):
    """TREAT_AS_NOT_FOUND: non-matching attribute becomes empty string, indistinguishable from unreadable.
    A second attribute with no expression passes and keeps the version in play."""
    from hope_documents.tasks import process_analysis_job

    attr_fail = Attribute.objects.get(name="first_name")
    attr_pass = Attribute.objects.get(name="last_name")
    doc = DocumentFactory(document_type=document_type, country=country, version="v1")
    DocumentAttributeFactory(document=doc, attribute=attr_fail, validation_expression=r"\d{9}")
    DocumentAttributeFactory(document=doc, attribute=attr_pass, validation_expression=None)

    job = _create_job_with_image(
        document_type, country, png_bytes, validation_mode=AnalysisJob.ValidationMode.TREAT_AS_NOT_FOUND
    )

    with patch("hope_documents.tasks.Processor") as mock_proc:
        # "JOHN" fails \d{9} → first_name treated as not found; last_name has no expression → passes
        mock_proc.return_value.find_single.return_value = ("JOHN", MagicMock())
        process_analysis_job(str(job.id))

    job.refresh_from_db()
    assert job.status == AnalysisJob.Status.COMPLETED
    assert job.version_matched is True
    first_name_result = next(a for a in job.result if a["attribute_name"] == "first_name")
    assert first_name_result["extracted_value"] == ""
    assert "is_valid" not in first_name_result


@pytest.mark.django_db
def test_task_fail_analysis_mode_invalid(document_type, country, png_bytes):
    """FAIL_ANALYSIS: a non-matching attribute immediately fails the entire job."""
    from hope_documents.tasks import process_analysis_job

    attr = Attribute.objects.get(name="first_name")
    doc = DocumentFactory(document_type=document_type, country=country, version="v1")
    DocumentAttributeFactory(document=doc, attribute=attr, validation_expression=r"\d{9}")

    job = _create_job_with_image(
        document_type, country, png_bytes, validation_mode=AnalysisJob.ValidationMode.FAIL_ANALYSIS
    )

    with patch("hope_documents.tasks.Processor") as mock_proc:
        mock_proc.return_value.find_single.return_value = ("JOHN", MagicMock())
        with pytest.raises(Exception, match="first_name"):
            process_analysis_job(str(job.id))

    job.refresh_from_db()
    assert job.status == AnalysisJob.Status.FAILED
    assert "first_name" in job.error


@pytest.mark.django_db
def test_region_extraction_uses_crop_when_region_set(document_type, country, png_bytes):
    """When DocumentAttribute has a region, OCRAttributeExtractor crops first; find_single not called."""
    from hope_documents.tasks import process_analysis_job
    from hope_ocr.archive.region import BoundingBox

    attr = Attribute.objects.get(name="first_name")
    doc = DocumentFactory(document_type=document_type, country=country, version="v1")
    DocumentAttributeFactory(document=doc, attribute=attr, region=BoundingBox.from_rect(0, 0, 10, 10))

    job = _create_job_with_image(document_type, country, png_bytes)

    with patch("hope_documents.tasks.Processor") as mock_proc:
        mock_proc.return_value.reader.extract.return_value = "MARIO"
        process_analysis_job(str(job.id))

    mock_proc.return_value.reader.extract.assert_called_once()
    mock_proc.return_value.find_single.assert_not_called()


@pytest.mark.django_db
def test_region_extraction_falls_back_to_full_image_when_crop_empty(document_type, country, png_bytes):
    """When cropped region returns empty string, OCRAttributeExtractor falls back to find_single."""
    from hope_documents.tasks import process_analysis_job
    from hope_ocr.archive.region import BoundingBox

    attr = Attribute.objects.get(name="first_name")
    doc = DocumentFactory(document_type=document_type, country=country, version="v1")
    DocumentAttributeFactory(document=doc, attribute=attr, region=BoundingBox.from_rect(0, 0, 10, 10))

    job = _create_job_with_image(document_type, country, png_bytes)

    with patch("hope_documents.tasks.Processor") as mock_proc:
        mock_proc.return_value.reader.extract.return_value = ""
        mock_proc.return_value.find_single.return_value = ("MARIO", MagicMock())
        process_analysis_job(str(job.id))

    mock_proc.return_value.reader.extract.assert_called_once()
    mock_proc.return_value.find_single.assert_called_once()


@pytest.mark.django_db
def test_region_extraction_falls_back_when_no_region(document_type, country, png_bytes):
    """Without a region, OCRAttributeExtractor uses find_single directly."""
    from hope_documents.tasks import process_analysis_job

    attr = Attribute.objects.get(name="first_name")
    doc = DocumentFactory(document_type=document_type, country=country, version="v1")
    DocumentAttributeFactory(document=doc, attribute=attr, region=None)

    job = _create_job_with_image(document_type, country, png_bytes)

    with patch("hope_documents.tasks.Processor") as mock_proc:
        mock_proc.return_value.find_single.return_value = ("MARIO", MagicMock())
        process_analysis_job(str(job.id))

    mock_proc.return_value.reader.extract.assert_not_called()
    mock_proc.return_value.find_single.assert_called()


# ---------------------------------------------------------------------------
# Sync mode (?sync=true)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_analyze_sync_returns_200_with_full_result(app, png_bytes, document_type, country):
    """`?sync=true` runs the task inline and returns the completed job payload with HTTP 200."""
    url = reverse("api:analyze-create") + "?sync=true"
    with patch("hope_documents.api.viewsets.analyze.process_analysis_job") as mock_task:
        mock_task.return_value = None
        response = app.post(
            url,
            params={"document_type": document_type.code, "country": country.code2},
            upload_files=[("image_file", "passport.png", png_bytes)],
        )
    assert response.status_code == status.HTTP_200_OK
    data = response.json
    assert "job_id" in data
    assert "status" in data
    assert "attributes" in data
    mock_task.assert_called_once()
    mock_task.delay.assert_not_called()


@pytest.mark.django_db
def test_analyze_async_returns_202_job_id(app, png_bytes, document_type, country):
    """Without ?sync=true the original 202 + job_id response is returned."""
    url = reverse("api:analyze-create")
    with patch("hope_documents.api.viewsets.analyze.process_analysis_job") as mock_task:
        mock_task.delay.return_value = None
        response = app.post(
            url,
            params={"document_type": document_type.code, "country": country.code2},
            upload_files=[("image_file", "passport.png", png_bytes)],
        )
    assert response.status_code == status.HTTP_202_ACCEPTED
    assert "job_id" in response.json
    mock_task.delay.assert_called_once()
    mock_task.assert_not_called()
