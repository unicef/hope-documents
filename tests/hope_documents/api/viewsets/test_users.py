import pytest
from django.urls import reverse
from factories.api_token import APITokenFactory
from factories.user import UserFactory
from rest_framework import status
from rest_framework.test import APIClient

from hope_documents.grants import Grant


@pytest.fixture
def token_client():
    token = APITokenFactory(grants=[Grant.API_PLAN_MANAGE.value])
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
    return client


@pytest.mark.django_db
def test_list_users(token_client):
    UserFactory.create_batch(3)
    url = reverse("api:user-list")
    response = token_client.get(url)
    assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
def test_list_users_unauthenticated():
    client = APIClient()
    url = reverse("api:user-list")
    response = client.get(url)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
def test_list_users_wrong_grant():
    token = APITokenFactory(grants=[Grant.API_OCR_EXTRACT.value])
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
    url = reverse("api:user-list")
    response = client.get(url)
    assert response.status_code == status.HTTP_403_FORBIDDEN
