from unittest.mock import patch

from django.core.checks import Error

from hope_documents.checks import check_dirs


def test_check_dirs_both_exist(tmp_path):
    """Test check_dirs when both MEDIA_ROOT and STATIC_ROOT exist."""
    media_root = tmp_path / "media"
    media_root.mkdir()
    static_root = tmp_path / "static"
    static_root.mkdir()

    with patch("hope_documents.checks.env") as mock_env:
        mock_env.side_effect = lambda key: (
            str(media_root) if key == "MEDIA_ROOT" else str(static_root)
        )
        errors = check_dirs()
        assert len(errors) == 0


def test_check_dirs_one_does_not_exist(tmp_path):
    """Test check_dirs when one of the directories does not exist."""
    media_root = tmp_path / "media"
    # media_root is not created
    static_root = tmp_path / "static"
    static_root.mkdir()

    with patch("hope_documents.checks.env") as mock_env:
        mock_env.side_effect = lambda key: (
            str(media_root) if key == "MEDIA_ROOT" else str(static_root)
        )
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
        mock_env.side_effect = lambda key: (
            str(media_root) if key == "MEDIA_ROOT" else str(static_root)
        )
        errors = check_dirs()
        assert len(errors) == 2
        assert isinstance(errors[0], Error)
        assert isinstance(errors[1], Error)
        assert "MEDIA_ROOT" in errors[0].msg
        assert "STATIC_ROOT" in errors[1].msg
