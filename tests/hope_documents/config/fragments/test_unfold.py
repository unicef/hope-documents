from unittest.mock import MagicMock

from django.test import override_settings

from hope_documents.config.fragments.unfold import badge_callback, environment_callback


def test_badge_callback():
    """Test that badge_callback returns an empty string."""
    request = MagicMock()
    assert badge_callback(request) == ""


@override_settings(ENVIRONMENT="test_env")
def test_environment_callback():
    """Test that environment_callback returns the correct environment name."""
    request = MagicMock()
    assert environment_callback(request) == ("test_env", "info")
