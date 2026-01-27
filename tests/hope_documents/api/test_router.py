import pytest
from django.urls import reverse
from factories.user import UserFactory
from rest_framework.test import APIClient


@pytest.mark.django_db
def test_api_root_unauthenticated():
    """
    GIVEN an unauthenticated user
    WHEN accessing the API root
    THEN a 401 Unauthorized response is returned.
    """
    client = APIClient()
    url = reverse("api:api-root")

    response = client.get(url)

    assert response.status_code == 401
    assert response.json() == {}


@pytest.mark.django_db
def test_api_root_authenticated():
    """
    GIVEN an authenticated user
    WHEN accessing the API root
    THEN a 200 OK response is returned with API endpoints.
    """
    user = UserFactory()
    client = APIClient()
    client.force_authenticate(user=user)
    url = reverse("api:api-root")

    response = client.get(url)

    assert response.status_code == 200
    # Check that it returns the list of endpoints, which is the default behavior
    assert "users" in response.json()
    assert "groups" in response.json()
