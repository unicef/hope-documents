from unittest.mock import MagicMock, call, patch

import pytest
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

    command.handle(**options)

    assert mock_call_command.call_count == 5
    mock_call_command.assert_has_calls(
        [
            call("check", deploy=True, verbosity=0),
            call("collectstatic", no_input=True, verbosity=0, stdout=command.stdout),
            call("migrate", no_input=True, verbosity=0, stdout=command.stdout),
            call("create_extra_permissions"),
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
