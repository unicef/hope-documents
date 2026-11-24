import pytest
from factories import SuperUserFactory
from factories.api_token import APITokenFactory


@pytest.fixture
def app(django_app_factory, mocked_responses):
    django_app = django_app_factory(csrf_checks=False)
    admin_user = SuperUserFactory()
    django_app.set_user(admin_user)
    django_app._user = admin_user
    token = APITokenFactory(user=admin_user)
    django_app.extra_environ["HTTP_AUTHORIZATION"] = f"Token {token.key}"
    return django_app
