from unittest.mock import MagicMock, call, patch

import pytest
from django.core.exceptions import ValidationError
from django.test import override_settings

from hope_documents.management.commands.upgrade import Command


def test_add_arguments():
    command = Command()
    parser = MagicMock()
    command.add_arguments(parser)
    assert parser.add_argument.call_count == 7


@pytest.mark.parametrize(
    ("options", "expected_prompt", "expected_static", "expected_migrate"),
    [
        (
            {
                "verbosity": 1,
                "checks": False,
                "prompt": False,
                "static": True,
                "migrate": True,
                "debug": False,
                "admin_email": "",
                "admin_password": "",
            },
            True,
            True,
            True,
        ),
        (
            {
                "verbosity": 0,
                "checks": True,
                "prompt": True,
                "static": False,
                "migrate": False,
                "debug": True,
                "admin_email": "test@test.com",
                "admin_password": "pw",
            },
            False,
            False,
            False,
        ),
    ],
)
def test_get_options(options, expected_prompt, expected_static, expected_migrate):
    command = Command()
    with patch("hope_documents.management.commands.upgrade.env", return_value=""):
        command.get_options(options)
    assert command.prompt == expected_prompt
    assert command.static == expected_static
    assert command.migrate == expected_migrate


@patch("hope_documents.management.commands.upgrade.call_command")
@patch("hope_documents.management.commands.upgrade.env", return_value="")
@patch("hope_documents.management.commands.upgrade.logger")
@patch("hope_documents.models.User")
@patch("hope_documents.management.commands.upgrade.os")
@patch("hope_documents.management.commands.upgrade.Path")
@patch("hope_documents.management.commands.upgrade.validate_email")
@override_settings(STATIC_ROOT="/tmp/static", FLAGS=["FLAG1", "FLAG2"])
def test_handle_all_options_true_no_admin(
    mock_validate_email, mock_path, mock_os, mock_user, mock_logger, mock_env, mock_call_command
):
    command = Command()
    command.stdout = MagicMock()
    command.style = MagicMock()

    options = {
        "verbosity": 1,
        "checks": True,
        "prompt": True,  # self.prompt will be False
        "static": True,
        "migrate": True,
        "debug": False,
        "admin_email": "",
        "admin_password": "",
    }

    mock_user.objects.filter.return_value.exists.return_value = False  # Admin user does not exist
    mock_path_instance = MagicMock()
    mock_path.return_value = mock_path_instance
    mock_path_instance.exists.return_value = False

    with patch.dict("os.environ", {}, clear=True):
        command.handle(**options)

    assert mock_call_command.call_count == 5
    mock_call_command.assert_has_calls(
        [
            call("check", deploy=True, verbosity=0),
            call("collectstatic", no_input=True, verbosity=0, stdout=command.stdout),
            call("migrate", no_input=True, verbosity=0, stdout=command.stdout),
            call("create_extra_permissions", no_input=True, verbosity=0, stdout=command.stdout),
            call("remove_stale_contenttypes", no_input=True, verbosity=0, stdout=command.stdout),
        ]
    )
    mock_path_instance.mkdir.assert_called_once_with(parents=True)
    mock_validate_email.assert_not_called()
    assert mock_os.environ.__setitem__.call_count == 0


@patch("hope_documents.management.commands.upgrade.call_command")
@patch("hope_documents.management.commands.upgrade.env", return_value="")
@patch("hope_documents.management.commands.upgrade.logger")
@patch("hope_documents.models.User")
@patch("hope_documents.management.commands.upgrade.os")
@patch("hope_documents.management.commands.upgrade.Path")
@patch("hope_documents.management.commands.upgrade.validate_email")
@override_settings(STATIC_ROOT="/tmp/static", FLAGS=[])
def test_handle_create_admin_user(
    mock_validate_email, mock_path, mock_os, mock_user, mock_logger, mock_env, mock_call_command
):
    command = Command()
    command.stdout = MagicMock()
    command.style = MagicMock()

    options = {
        "verbosity": 1,
        "checks": False,
        "prompt": True,  # self.prompt will be False
        "static": False,
        "migrate": False,
        "debug": False,
        "admin_email": "test@example.com",
        "admin_password": "password",
    }

    mock_user.objects.filter.return_value.exists.return_value = False  # Admin user does not exist

    with patch.dict("os.environ", {}, clear=True):
        command.handle(**options)

    mock_user.objects.filter.assert_called_once_with(email="test@example.com")
    mock_validate_email.assert_called_once_with("test@example.com")
    assert mock_os.environ.__setitem__.call_count == 3
    mock_os.environ.__setitem__.assert_has_calls(
        [
            call("DJANGO_SUPERUSER_USERNAME", "test@example.com"),
            call("DJANGO_SUPERUSER_EMAIL", "test@example.com"),
            call("DJANGO_SUPERUSER_PASSWORD", "password"),
        ]
    )
    assert mock_call_command.call_count == 2
    mock_call_command.assert_has_calls(
        [
            call("remove_stale_contenttypes", no_input=True, verbosity=0, stdout=command.stdout),
            call(
                "createsuperuser", email="test@example.com", username="test@example.com", verbosity=0, interactive=False
            ),
        ]
    )


@patch("hope_documents.management.commands.upgrade.call_command")
@patch("hope_documents.management.commands.upgrade.env", return_value="")
@patch("hope_documents.management.commands.upgrade.logger")
@patch("hope_documents.models.User")
@patch("hope_documents.management.commands.upgrade.os")
@patch("hope_documents.management.commands.upgrade.Path")
@patch("hope_documents.management.commands.upgrade.validate_email")
@override_settings(STATIC_ROOT="/tmp/static", FLAGS=[])
def test_handle_admin_user_exists(
    mock_validate_email, mock_path, mock_os, mock_user, mock_logger, mock_env, mock_call_command
):
    command = Command()
    command.stdout = MagicMock()
    command.style = MagicMock()

    options = {
        "verbosity": 1,
        "checks": False,
        "prompt": True,  # self.prompt will be False
        "static": False,
        "migrate": False,
        "debug": False,
        "admin_email": "test@example.com",
        "admin_password": "password",
    }

    mock_user.objects.filter.return_value.exists.return_value = True  # Admin user exists

    with patch.dict("os.environ", {}, clear=True):
        command.handle(**options)

    mock_user.objects.filter.assert_called_once_with(email="test@example.com")
    mock_validate_email.assert_not_called()
    assert mock_os.environ.__setitem__.call_count == 0
    assert mock_call_command.call_count == 1
    mock_call_command.assert_has_calls(
        [
            call("remove_stale_contenttypes", no_input=True, verbosity=0, stdout=command.stdout),
        ]
    )

@patch("hope_documents.management.commands.upgrade.call_command")
@patch("hope_documents.management.commands.upgrade.env", return_value="")
@patch("hope_documents.management.commands.upgrade.logger")
@patch("hope_documents.models.User")
@patch("hope_documents.management.commands.upgrade.os")
@patch("hope_documents.management.commands.upgrade.Path")
@patch("hope_documents.management.commands.upgrade.validate_email")
@override_settings(STATIC_ROOT="/tmp/static", FLAGS=["FLAG1", "FLAG2"])
def test_handle_verbosity_zero(
    mock_validate_email, mock_path, mock_os, mock_user, mock_logger, mock_env, mock_call_command
):
    command = Command()
    command.stdout = MagicMock()
    command.style = MagicMock()

    options = {
        "verbosity": 0,  # This will trigger the `else` branch for `echo`
        "checks": True,
        "prompt": True,  # self.prompt will be False
        "static": True,
        "migrate": True,
        "debug": False,
        "admin_email": "",
        "admin_password": "",
    }

    mock_user.objects.filter.return_value.exists.return_value = False
    mock_path_instance = MagicMock()
    mock_path.return_value = mock_path_instance
    mock_path_instance.exists.return_value = False

    with patch.dict("os.environ", {}, clear=True):
        command.handle(**options)

    # In verbosity=0, echo is a lambda that does nothing, so stdout.write should not be called
    command.stdout.write.assert_not_called()
    assert mock_call_command.call_count == 5
    mock_call_command.assert_has_calls(
        [
            call("check", deploy=True, verbosity=-1), # verbosity-1 is -1 when verbosity is 0
            call("collectstatic", no_input=True, verbosity=-1, stdout=command.stdout),
            call("migrate", no_input=True, verbosity=-1, stdout=command.stdout),
            call("create_extra_permissions", no_input=True, verbosity=-1, stdout=command.stdout),
            call("remove_stale_contenttypes", no_input=True, verbosity=-1, stdout=command.stdout),
        ]
    )

@patch("hope_documents.management.commands.upgrade.call_command")
@patch("hope_documents.management.commands.upgrade.env", return_value="")
@patch("hope_documents.management.commands.upgrade.logger")
@patch("hope_documents.models.User")
@patch("hope_documents.management.commands.upgrade.os")
@patch("hope_documents.management.commands.upgrade.Path")
@patch("hope_documents.management.commands.upgrade.validate_email")
@override_settings(STATIC_ROOT="/tmp/static", FLAGS=["FLAG1", "FLAG2"])
def test_handle_validation_error(
    mock_validate_email, mock_path, mock_os, mock_user, mock_logger, mock_env, mock_call_command
):
    command = Command()
    command.stdout = MagicMock()
    command.style = MagicMock()

    options = {
        "verbosity": 1,
        "checks": False,
        "prompt": True,
        "static": True,
        "migrate": True,
        "debug": True, # Set debug to True
        "admin_email": "invalid-email", # This will cause validate_email to fail
        "admin_password": "password",
    }

    mock_user.objects.filter.return_value.exists.return_value = False
    mock_path_instance = MagicMock()
    mock_path.return_value = mock_path_instance
    mock_path_instance.exists.return_value = False

    # Mock validate_email to raise ValidationError
    mock_validate_email.side_effect = ValidationError("Invalid email")

    with patch.dict("os.environ", {}, clear=True):
        with pytest.raises(ValidationError) as excinfo:  # Expect Exception to be re-raised
            command.handle(**options)
        # Verify the exception message
        assert "Invalid email" in str(excinfo.value)

    command.stdout.write.assert_called()
    mock_validate_email.assert_called_once_with("invalid-email")
    mock_logger.exception.assert_not_called()


@patch("hope_documents.management.commands.upgrade.call_command", side_effect=Exception("Generic error"))
@patch("hope_documents.management.commands.upgrade.env", return_value="")
@patch("hope_documents.management.commands.upgrade.logger")
@patch("hope_documents.models.User")
@patch("hope_documents.management.commands.upgrade.os")
@patch("hope_documents.management.commands.upgrade.Path")
@patch("hope_documents.management.commands.upgrade.validate_email")
@override_settings(STATIC_ROOT="/tmp/static", FLAGS=["FLAG1", "FLAG2"])
def test_handle_general_exception(
    mock_validate_email, mock_path, mock_os, mock_user, mock_logger, mock_env, mock_call_command
):
    command = Command()
    command.stdout = MagicMock()
    command.style = MagicMock()

    options = {
        "verbosity": 1,
        "checks": True, # This will trigger the first call_command
        "prompt": True,
        "static": True,
        "migrate": True,
        "debug": True, # Set debug to True
        "admin_email": "",
        "admin_password": "",
    }

    mock_user.objects.filter.return_value.exists.return_value = False
    mock_path_instance = MagicMock()
    mock_path.return_value = mock_path_instance
    mock_path_instance.exists.return_value = False

    with patch.dict("os.environ", {}, clear=True):
        with pytest.raises(Exception, match="Generic error") as excinfo: # Expect generic Exception to be re-raised
            command.handle(**options)
        # Verify the exception message
        assert "Generic error" in str(excinfo.value)

    command.stdout.write.assert_called()
    mock_logger.exception.assert_called_once()
