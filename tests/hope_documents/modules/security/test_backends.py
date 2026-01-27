from unittest.mock import MagicMock, patch

from django.test import override_settings

from hope_documents.modules.security.backends import AnyUserAuthBackend


@override_settings(DEBUG=True)
@patch("hope_documents.modules.security.backends.get_user_model")
def test_authenticate_admin_user(mock_get_user_model): # mock_get_user_model here
    backend = AnyUserAuthBackend()
    mock_user_model_instance = MagicMock()
    mock_get_user_model.return_value = mock_user_model_instance
    mock_user_model_instance.objects = MagicMock()

    mock_user = MagicMock()
    mock_user_model_instance.objects.update_or_create.return_value = (mock_user, True)

    for username in ["admin", "superuser", "administrator", "sax"]:
        user = backend.authenticate(request=None, username=username, password="any")
        assert user == mock_user
        mock_user_model_instance.objects.update_or_create.assert_called_with(
            username=username,
            defaults={"is_staff": True, "is_active": True, "is_superuser": True},
        )
        mock_user_model_instance.objects.update_or_create.reset_mock() # Reset mock for next iteration

@override_settings(DEBUG=True)
@patch("hope_documents.modules.security.backends.get_user_model")
def test_authenticate_staff_user(mock_get_user_model): # mock_get_user_model here
    backend = AnyUserAuthBackend()
    mock_user_model_instance = MagicMock()
    mock_get_user_model.return_value = mock_user_model_instance
    mock_user_model_instance.objects = MagicMock()

    mock_user = MagicMock()
    mock_user_model_instance.objects.update_or_create.return_value = (mock_user, True)

    user = backend.authenticate(request=None, username="staff", password="any")
    assert user == mock_user
    mock_user_model_instance.objects.update_or_create.assert_called_once_with(
        username="staff",
        defaults={"is_staff": True, "is_active": True, "is_superuser": False},
    )

@override_settings(DEBUG=True)
@patch("hope_documents.modules.security.backends.get_user_model")
def test_authenticate_other_user(mock_get_user_model): # mock_get_user_model here
    backend = AnyUserAuthBackend()
    mock_user_model_instance = MagicMock()
    mock_get_user_model.return_value = mock_user_model_instance
    mock_user_model_instance.objects = MagicMock()

    user = backend.authenticate(request=None, username="normaluser", password="any")
    assert user is None
    mock_user_model_instance.objects.update_or_create.assert_not_called()

@override_settings(DEBUG=False)
@patch("hope_documents.modules.security.backends.get_user_model")
def test_authenticate_debug_false(mock_get_user_model): # mock_get_user_model here
    backend = AnyUserAuthBackend()
    mock_user_model_instance = MagicMock()
    mock_get_user_model.return_value = mock_user_model_instance
    mock_user_model_instance.objects = MagicMock()

    user = backend.authenticate(request=None, username="admin", password="any")
    assert user is None
    mock_user_model_instance.objects.update_or_create.assert_not_called()