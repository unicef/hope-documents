import io

import pytest
from PIL import Image
from django.urls import reverse
from factories.api_token import APITokenFactory
from rest_framework import status

from hope_ocr.ocr.engine import MatchMode


@pytest.fixture
def token():
    return APITokenFactory()


@pytest.fixture
def image(app, text="test text"):
    img = Image.new("RGB", (100, 50), color="white")
    image_file = io.BytesIO()
    img.save(image_file, "png")
    image_file.name = "test.png"
    image_file.seek(0)
    return image_file


def _token_headers(token):
    return {"Authorization": f"Token {token.key}"}


@pytest.mark.django_db
def test_extract_without_pattern(app, token, image):
    url = reverse("api:file-upload")
    image.seek(0)
    response = app.post(
        url,
        upload_files=[
            ("attachment", image.name, image.read()),
        ],
        headers=_token_headers(token),
    )
    assert response.status_code == status.HTTP_200_OK
    assert "loaders" in response.json
    assert "params" in response.json
    assert "info" in response.json


@pytest.mark.django_db
def test_extract_with_pattern(app, token, image):
    url = reverse("api:file-upload")

    response = app.post(
        url,
        params={
            "pattern": "test",
            "mode": MatchMode.FIRST.value,
            "rotate": 0,
        },
        upload_files=[
            ("attachment", image.name, image.read()),
        ],
        headers=_token_headers(token),
    )

    assert response.status_code == status.HTTP_200_OK
    assert "findings" in response.json
    assert "params" in response.json


@pytest.mark.django_db
def test_extract_with_non_image_file(app, token):
    file_content = b"this is not an image"
    url = reverse("api:file-upload")
    response = app.post(
        url,
        upload_files=[
            ("attachment", "test.txt", file_content),
        ],
        headers=_token_headers(token),
    )
    assert response.status_code == status.HTTP_200_OK
    assert "file" in response.json
    assert response.json["file"] is None


@pytest.mark.django_db
def test_extract_invalid_request(app, token):
    url = reverse("api:file-upload")
    response = app.post(url, headers=_token_headers(token), status=400)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "attachment" in response.json


@pytest.mark.django_db
def test_extract_unauthenticated(app):
    url = reverse("api:file-upload")
    response = app.post(url, status=401)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
