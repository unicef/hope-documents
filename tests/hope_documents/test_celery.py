from unittest.mock import patch


@patch("django.conf.settings")
@patch("os.environ.setdefault")
@patch("celery.Celery")
def test_celery_app_setup(mock_celery_class, mock_setdefault, mock_settings):  # Note argument order
    # Clear the module from sys.modules to ensure a fresh import
    import sys

    if "hope_documents.celery" in sys.modules:
        del sys.modules["hope_documents.celery"]

    mock_settings.CELERY_BROKER_URL = "redis://localhost:6379/0"

    from hope_documents.config import celery  # noqa: F401

    mock_setdefault.assert_called_once_with("DJANGO_SETTINGS_MODULE", "hope_documents.config.settings")

    mock_celery_class.assert_called_once_with(
        "hope_documents",
        loglevel="error",
        broker=mock_settings.CELERY_BROKER_URL,
    )

    mock_celery_class.return_value.config_from_object.assert_called_once_with(
        "django.conf:settings", namespace="CELERY", force=True
    )
    mock_celery_class.return_value.autodiscover_tasks.assert_called_once_with()
