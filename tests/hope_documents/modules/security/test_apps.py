from unittest.mock import Mock

import pytest
from django.contrib.auth.signals import user_logged_in
from django.test import override_settings

from hope_documents.models import User
from hope_documents.modules.security.apps import on_login


@pytest.fixture(autouse=True)
def _disconnect_signal():
    user_logged_in.disconnect(on_login)
    yield
    user_logged_in.connect(on_login)


@pytest.mark.django_db
@override_settings(SUPERUSERS=["super@user.com"])
def test_on_login_superuser_by_email():
    """Test that a user becomes a superuser if their email is in SUPERUSERS."""
    user = User.objects.create_user(
        email="super@user.com",
        username="super_email",
        is_superuser=False,
        is_staff=False,
    )
    on_login(sender=Mock(), user=user)
    user.refresh_from_db()
    assert user.is_superuser
    assert user.is_staff


@pytest.mark.django_db
@override_settings(SUPERUSERS=["super"])
def test_on_login_superuser_by_username():
    """Test that a user becomes a superuser if their username is in SUPERUSERS."""
    user = User.objects.create_user(username="super", email="super@example.com", is_superuser=False, is_staff=False)
    on_login(sender=Mock(), user=user)
    user.refresh_from_db()
    assert user.is_superuser
    assert user.is_staff


@pytest.mark.django_db
@override_settings(SUPERUSERS=["super@user.com"])
def test_on_login_not_superuser():
    """Test that a user does not become a superuser if they are not in SUPERUSERS."""
    user = User.objects.create_user(
        username="normaluser",
        email="normal@user.com",
        is_superuser=False,
        is_staff=False,
    )
    on_login(sender=Mock(), user=user)
    user.refresh_from_db()
    assert not user.is_superuser
    assert not user.is_staff


def test_on_login_anonymous_user():
    """Test that an anonymous user does not cause an error."""
    user = Mock()
    user.is_anonymous = True
    on_login(sender=Mock(), user=user)
    assert not user.save.called
