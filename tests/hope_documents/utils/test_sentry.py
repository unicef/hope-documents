from unittest.mock import patch

from hope_documents.utils.sentry import capture_exception


@patch("hope_documents.utils.sentry._capture_exception")
def test_capture_exception(mock_capture_exception):
    """Test that capture_exception calls the underlying sentry function."""
    error = ValueError("test error")
    capture_exception(error)
    mock_capture_exception.assert_called_once_with(error)


def test_capture_exception_with_none():
    """Test that capture_exception can be called with None."""
    capture_exception(None)
