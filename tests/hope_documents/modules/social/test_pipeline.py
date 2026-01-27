from unittest.mock import MagicMock, patch

from hope_documents.modules.social.pipeline import save_to_group


@patch("hope_documents.modules.social.pipeline.Group")
@patch("hope_documents.modules.social.pipeline.config")
def test_save_to_group_with_user_and_config(mock_config, mock_group):
    mock_config.NEW_USER_DEFAULT_GROUP = "Default Group"
    mock_user = MagicMock()
    mock_group_instance = MagicMock()
    mock_group.objects.get.return_value = mock_group_instance

    result = save_to_group(backend=MagicMock(), user=mock_user)

    mock_group.objects.get.assert_called_once_with(name="Default Group")
    mock_user.groups.add.assert_called_once_with(mock_group_instance)
    assert result == {}


@patch("hope_documents.modules.social.pipeline.Group")
@patch("hope_documents.modules.social.pipeline.config")
def test_save_to_group_no_user(mock_config, mock_group):
    mock_config.NEW_USER_DEFAULT_GROUP = "Default Group"

    result = save_to_group(backend=MagicMock(), user=None)

    mock_group.objects.get.assert_not_called()
    assert result == {}


@patch("hope_documents.modules.social.pipeline.Group")
@patch("hope_documents.modules.social.pipeline.config")
def test_save_to_group_no_default_group_config(mock_config, mock_group):
    mock_config.NEW_USER_DEFAULT_GROUP = None
    mock_user = MagicMock()

    result = save_to_group(backend=MagicMock(), user=mock_user)

    mock_group.objects.get.assert_not_called()
    mock_user.groups.add.assert_not_called()
    assert result == {}
