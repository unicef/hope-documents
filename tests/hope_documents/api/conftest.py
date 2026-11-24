import pytest
from factories.api_token import APITokenFactory
from rest_framework.test import APIClient

from hope_documents.grants import Grant


@pytest.fixture
def api_token():
    return APITokenFactory()


@pytest.fixture
def token_client(api_token):
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Token {api_token.key}")
    return client


@pytest.fixture
def plan_manage_token_client():
    token = APITokenFactory(grants=[Grant.API_PLAN_MANAGE.value])
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
    return client
