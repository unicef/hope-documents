import io

import pytest
from PIL import Image
from django.urls import reverse
from factories.api_token import APITokenFactory
from rest_framework import status
from rest_framework.test import APIClient

from hope_ocr.ocr.engine import MatchMode


@pytest.fixture
def token_client():
    token = APITokenFactory()
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
    return client


@pytest.fixture
def image():
    img = Image.new("RGB", (100, 50), color="white")
    image_file = io.BytesIO()
    img.save(image_file, "png")
    image_file.name = "test.png"
    image_file.seek(0)
    return image_file


@pytest.mark.django_db
def test_extract_without_pattern(token_client, image):
    url = reverse("api:file-upload")
    image.seek(0)
    response = token_client.post(url, {"attachment": image}, format="multipart")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "loaders" in data
    assert "params" in data
    assert "info" in data


@pytest.mark.django_db
def test_extract_with_pattern(token_client, image):
    url = reverse("api:file-upload")
    image.seek(0)
    response = token_client.post(
        url,
        {
            "attachment": image,
            "pattern": "test",
            "mode": MatchMode.FIRST.value,
            "rotate": 0,
        },
        format="multipart",
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "findings" in data
    assert "params" in data


@pytest.mark.django_db
def test_extract_with_non_image_file(token_client):
    file_content = io.BytesIO(b"this is not an image")
    file_content.name = "test.txt"
    url = reverse("api:file-upload")
    response = token_client.post(url, {"attachment": file_content}, format="multipart")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "file" in data
    assert data["file"] is None


@pytest.mark.django_db
def test_extract_invalid_request(token_client):
    url = reverse("api:file-upload")
    response = token_client.post(url, {}, format="multipart")
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "attachment" in response.json()


@pytest.mark.django_db
def test_extract_unauthenticated():
    client = APIClient()
    url = reverse("api:file-upload")
    response = client.post(url, {}, format="multipart")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
