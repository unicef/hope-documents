import pytest
from django.test import Client
from django.urls import reverse


@pytest.mark.django_db
def test_healthcheck(client: Client) -> None:
    """Test the healthcheck view."""
    response = client.get(reverse("healthcheck"))
    assert response.status_code == 200
    assert response.content == b"OK"


@pytest.mark.django_db
def test_index(client: Client) -> None:
    """Test the index view."""
    response = client.get(reverse("home"))
    assert response.status_code == 200
    assert "home.html" in [t.name for t in response.templates]
