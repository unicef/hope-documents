from unittest.mock import MagicMock, patch

import pytest
from django.conf import settings
from django.test import override_settings

from flags.models import FlagState
from hope_documents.management.commands.develop import Command, DEFAULT_GROUP_NAME


@pytest.fixture
def command():
    """Fixture for command instance."""
    cmd = Command()
    cmd.stdout = MagicMock()
    return cmd


@patch("hope_documents.management.commands.develop.call_command")
@patch("hope_documents.management.commands.develop.Site")
@patch("hope_documents.management.commands.develop.Group")
@patch("hope_documents.management.commands.develop.config")
@patch("hope_documents.management.commands.develop.FlagState.objects.bulk_create")
@override_settings(DEBUG=True, FLAGS=["FLAG1", "FLAG2"])
def test_handle_debug_true(
    mock_bulk_create, mock_config, mock_group, mock_site, mock_call_command, command
):
    """Test develop command when DEBUG is True."""
    # Setup mocks
    mock_site.objects.update_or_create.return_value = (MagicMock(), True)
    mock_group.objects.get_or_create.return_value = (MagicMock(), True)

    command.handle()

    mock_call_command.assert_called_once_with("upgrade")
    mock_site.objects.update_or_create.assert_called_once_with(
        pk=settings.SITE_ID, defaults={"domain": "localhost:8000", "name": "localhost"}
    )
    mock_site.objects.clear_cache.assert_called_once()
    mock_group.objects.get_or_create.assert_called_once_with(name=DEFAULT_GROUP_NAME)
    assert mock_config.NEW_USER_DEFAULT_GROUP == DEFAULT_GROUP_NAME
    mock_bulk_create.assert_called_once()

    # Assert the arguments passed to bulk_create
    args, kwargs = mock_bulk_create.call_args
    flag_states = args[0]
    assert len(flag_states) == 2
    # Assert that the created objects are actual FlagState instances and have correct attributes
    assert isinstance(flag_states[0], FlagState)
    assert flag_states[0].name == "FLAG1"
    assert flag_states[0].value == "127.0.0.1,localhost"
    assert isinstance(flag_states[1], FlagState)
    assert flag_states[1].name == "FLAG2"
    assert flag_states[1].value == "127.0.0.1,localhost"
    assert kwargs["ignore_conflicts"] is True

    command.stdout.write.assert_any_call(
        "Starting configuring development environment", command.style.WARNING
    )
    command.stdout.write.assert_any_call("Configuring site settings")
    command.stdout.write.assert_any_call("Creating default group")
    command.stdout.write.assert_any_call("Setting up flags")


@patch("hope_documents.management.commands.develop.call_command")
@patch("hope_documents.management.commands.develop.Site")
@patch("hope_documents.management.commands.develop.Group")
@patch("hope_documents.management.commands.develop.config")
@patch("hope_documents.management.commands.develop.FlagState.objects.bulk_create")
@override_settings(DEBUG=False, FLAGS=["FLAG1", "FLAG2"])
def test_handle_debug_false(
    mock_bulk_create, mock_config, mock_group, mock_site, mock_call_command, command
):
    """Test develop command when DEBUG is False."""
    command.handle()

    command.stdout.write.assert_any_call(
        "Starting configuring development environment", command.style.WARNING
    )
    command.stdout.write.assert_any_call(
        "This command can be used only if DEBUG is True", command.style.ERROR
    )
    mock_call_command.assert_not_called()
    mock_site.objects.update_or_create.assert_not_called()
    mock_site.objects.clear_cache.assert_not_called()
    mock_group.objects.get_or_create.assert_not_called()
    mock_bulk_create.assert_not_called()
