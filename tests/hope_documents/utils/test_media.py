from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

import pytest
from django.core.files.storage import Storage
from django.http import Http404, StreamingHttpResponse
from django.test import override_settings

from hope_documents.utils.media import download_media, resource_path


@override_settings(PACKAGE_DIR="/test/package/dir")
def test_resource_path():
    path = "some/resource"
    expected = Path("/test/package/dir") / path
    assert resource_path(path) == expected


def test_download_media_file_exists():
    mock_storage = MagicMock(spec=Storage)
    mock_storage.path.return_value = "/fake/path/to/file.txt"
    mock_storage.exists.return_value = True

    with patch("builtins.open", mock_open(read_data=b"file content")):
        response = download_media("file.txt", storage=mock_storage)

    assert isinstance(response, StreamingHttpResponse)
    assert response.status_code == 200
    assert response["Content-Disposition"] == "inline; filename=file.txt"
    mock_storage.path.assert_called_once_with("file.txt")
    mock_storage.exists.assert_called_once_with("/fake/path/to/file.txt")


def test_download_media_file_does_not_exist():
    mock_storage = MagicMock(spec=Storage)
    mock_storage.path.return_value = "/fake/path/to/file.txt"
    mock_storage.exists.return_value = False

    with pytest.raises(Http404):
        download_media("file.txt", storage=mock_storage)

    mock_storage.path.assert_called_once_with("file.txt")
    mock_storage.exists.assert_called_once_with("/fake/path/to/file.txt")


@patch("hope_documents.utils.media.default_storage")
def test_download_media_no_storage_provided(mock_default_storage):
    mock_default_storage.path.return_value = "/fake/path/to/file.txt"
    mock_default_storage.exists.return_value = True

    with patch("builtins.open", mock_open(read_data=b"file content")):
        response = download_media("file.txt")

    assert isinstance(response, StreamingHttpResponse)
    assert response.status_code == 200
    mock_default_storage.path.assert_called_once_with("file.txt")
    mock_default_storage.exists.assert_called_once_with("/fake/path/to/file.txt")
