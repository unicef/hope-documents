import pytest
from django.urls import path

from hope_documents.exception import FlowTimeoutError


def view_that_raises_flow_timeout(request):
    raise FlowTimeoutError


def view_that_raises_other_exception(request):
    raise ValueError("message")


urlpatterns = [
    path("raise-flow-timeout/", view_that_raises_flow_timeout),
    path("raise-other-exception/", view_that_raises_other_exception),
]


@pytest.mark.urls(__name__)
@pytest.mark.django_db
def test_process_exception_handles_flow_timeout_error(client):
    response = client.get("/raise-flow-timeout/")
    assert response.status_code == 302
    assert response.url == "/"


@pytest.mark.urls(__name__)
@pytest.mark.django_db
def test_process_exception_ignores_other_exceptions(client):
    with pytest.raises(ValueError, match="message"):
        client.get("/raise-other-exception/")
