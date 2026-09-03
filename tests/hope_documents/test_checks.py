from unittest.mock import MagicMock, patch

from django.core.checks import Error
from django.core.checks import Warning as CheckWarning
from django.test import override_settings

from hope_documents.checks import check_dirs, check_hope_storage


class _BoomStorage:
    def __init__(self, **kwargs: object) -> None:
        raise ValueError("bad options")


class _FakeAzureStorage:
    def __init__(self, **kwargs: object) -> None:
        self.client = kwargs.get("client")


_FakeAzureStorage.__module__ = "storages.backends.azure_storage"


def test_check_dirs_both_exist(tmp_path):
    """Test check_dirs when both MEDIA_ROOT and STATIC_ROOT exist."""
    media_root = tmp_path / "media"
    media_root.mkdir()
    static_root = tmp_path / "static"
    static_root.mkdir()

    with patch("hope_documents.checks.env") as mock_env:
        mock_env.side_effect = lambda key: str(media_root) if key == "MEDIA_ROOT" else str(static_root)
        errors = check_dirs()
        assert len(errors) == 0


def test_check_dirs_one_does_not_exist(tmp_path):
    """Test check_dirs when one of the directories does not exist."""
    media_root = tmp_path / "media"
    # media_root is not created
    static_root = tmp_path / "static"
    static_root.mkdir()

    with patch("hope_documents.checks.env") as mock_env:
        mock_env.side_effect = lambda key: str(media_root) if key == "MEDIA_ROOT" else str(static_root)
        errors = check_dirs()
        assert len(errors) == 1
        assert isinstance(errors[0], Error)
        assert "MEDIA_ROOT" in errors[0].msg
        assert errors[0].id == "hope_documents.E005"


def test_check_dirs_both_do_not_exist(tmp_path):
    """Test check_dirs when both directories do not exist."""
    media_root = tmp_path / "media"
    static_root = tmp_path / "static"

    with patch("hope_documents.checks.env") as mock_env:
        mock_env.side_effect = lambda key: str(media_root) if key == "MEDIA_ROOT" else str(static_root)
        errors = check_dirs()
        assert len(errors) == 2
        assert isinstance(errors[0], Error)
        assert isinstance(errors[1], Error)
        assert "MEDIA_ROOT" in errors[0].msg
        assert "STATIC_ROOT" in errors[1].msg


def _hope_storages(backend: str, options: dict | None = None) -> dict:
    return {"hope": {"BACKEND": backend, "OPTIONS": options or {}}}


def test_check_hope_storage_missing():
    with override_settings(STORAGES={}):
        errors = check_hope_storage()
    assert len(errors) == 1
    assert errors[0].id == "hope_documents.storages.E001"


def test_check_hope_storage_invalid_backend():
    with override_settings(STORAGES=_hope_storages("does.not.exist.Storage")):
        errors = check_hope_storage()
    assert len(errors) == 1
    assert errors[0].id == "hope_documents.storages.E004"


def test_check_hope_storage_construct_error():
    with (
        patch("hope_documents.checks.import_string", return_value=_BoomStorage),
        override_settings(STORAGES=_hope_storages("boom")),
    ):
        errors = check_hope_storage()
    assert len(errors) == 1
    assert errors[0].id == "hope_documents.storages.E005"


def test_check_hope_storage_non_azure_warns():
    with override_settings(
        STORAGES=_hope_storages("django.core.files.storage.FileSystemStorage"),
    ):
        messages = check_hope_storage()
    assert len(messages) == 1
    assert isinstance(messages[0], CheckWarning)
    assert messages[0].id == "hope_documents.storages.W001"


def test_check_hope_storage_azure_empty_options():
    with override_settings(
        STORAGES=_hope_storages("storages.backends.azure_storage.AzureStorage"),
    ):
        errors = check_hope_storage()
    assert len(errors) == 1
    assert errors[0].id == "hope_documents.storages.E002"


def test_check_hope_storage_azure_container_missing():
    client = MagicMock()
    client.exists.return_value = False
    with (
        patch("hope_documents.checks.import_string", return_value=_FakeAzureStorage),
        override_settings(STORAGES=_hope_storages("azure", {"client": client})),
    ):
        errors = check_hope_storage()
    assert len(errors) == 1
    assert isinstance(errors[0], Error)
    assert errors[0].id == "hope_documents.storages.E003"
    assert "does not exist" in errors[0].msg


def test_check_hope_storage_azure_network_is_warning():
    client = MagicMock()
    client.exists.side_effect = ConnectionError("timed out")
    with (
        patch("hope_documents.checks.import_string", return_value=_FakeAzureStorage),
        override_settings(STORAGES=_hope_storages("azure", {"client": client})),
    ):
        messages = check_hope_storage()
    assert len(messages) == 1
    assert isinstance(messages[0], CheckWarning)
    assert messages[0].id == "hope_documents.storages.W002"


def test_check_hope_storage_azure_auth_is_error():
    client = MagicMock()
    client.exists.side_effect = RuntimeError("not authorized")
    with (
        patch("hope_documents.checks.import_string", return_value=_FakeAzureStorage),
        override_settings(STORAGES=_hope_storages("azure", {"client": client})),
    ):
        errors = check_hope_storage()
    assert len(errors) == 1
    assert isinstance(errors[0], Error)
    assert errors[0].id == "hope_documents.storages.E003"


def test_check_hope_storage_azure_ok():
    client = MagicMock()
    client.exists.return_value = True
    with (
        patch("hope_documents.checks.import_string", return_value=_FakeAzureStorage),
        override_settings(STORAGES=_hope_storages("azure", {"client": client})),
    ):
        assert check_hope_storage() == []


def test_check_hope_storage_azure_network_named_exception():
    class ServiceRequestError(Exception):
        pass

    ServiceRequestError.__module__ = "azure.core.exceptions"
    client = MagicMock()
    client.exists.side_effect = ServiceRequestError("no route")
    with (
        patch("hope_documents.checks.import_string", return_value=_FakeAzureStorage),
        override_settings(STORAGES=_hope_storages("azure", {"client": client})),
    ):
        messages = check_hope_storage()
    assert messages[0].id == "hope_documents.storages.W002"


def test_check_hope_storage_azure_without_client():
    with (
        patch("hope_documents.checks.import_string", return_value=_FakeAzureStorage),
        override_settings(STORAGES=_hope_storages("azure", {"account_name": "dev"})),
    ):
        assert check_hope_storage() == []
