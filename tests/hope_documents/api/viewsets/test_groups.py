import pytest
from django.urls import reverse
from factories.api_token import APITokenFactory
from factories.user import GroupFactory
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
def test_list_groups(token_client):
    GroupFactory.create_batch(3)
    url = reverse("api:group-list")
    response = token_client.get(url)
    assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
def test_list_groups_unauthenticated():
    client = APIClient()
    url = reverse("api:group-list")
    response = client.get(url)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
def test_list_groups_wrong_grant():
    token = APITokenFactory(grants=[Grant.API_OCR_EXTRACT.value])
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
    url = reverse("api:group-list")
    response = client.get(url)
    assert response.status_code == status.HTTP_403_FORBIDDEN
