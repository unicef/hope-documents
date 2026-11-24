import pytest
from django.urls import reverse
from factories.api_token import APITokenFactory
from factories.user import UserFactory
from rest_framework.test import APIClient


@pytest.fixture
def api_user():
    return UserFactory.create()


@pytest.mark.django_db
def test_api_root_unauthenticated():
    client = APIClient()
    url = reverse("api:api-root")

    response = client.get(url)

    assert response.status_code == 401
    assert response.json() == {"detail": "Authentication credentials were not provided."}


@pytest.mark.django_db
def test_api_root_authenticated(api_user):
    client = APIClient()
    client.force_authenticate(user=api_user)
    url = reverse("api:api-root")

    response = client.get(url)

    assert response.status_code == 200
    assert "users" in response.json()
    assert "groups" in response.json()


@pytest.mark.django_db
def test_api_root_token_authenticated():
    token = APITokenFactory()
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
    url = reverse("api:api-root")

    response = client.get(url)

    assert response.status_code == 200
    assert "users" in response.json()
    assert "groups" in response.json()
