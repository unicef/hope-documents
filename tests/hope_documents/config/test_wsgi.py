from unittest.mock import patch, MagicMock

from django.test import TestCase


from unittest.mock import patch, MagicMock

from django.test import TestCase


class WSGITest(TestCase):
    @patch("os.environ.setdefault") # Patch the actual function called
    @patch("django.core.wsgi.get_wsgi_application") # Patch the actual function called
    def test_wsgi_application_setup(self, mock_get_wsgi_application, mock_setdefault):
        # Clear the module from sys.modules to ensure a fresh import
        # This is crucial for testing module-level side effects
        import sys
        if "hope_documents.config.wsgi" in sys.modules:
            del sys.modules["hope_documents.config.wsgi"]

        # Now, import wsgi to trigger the module-level code with mocks active
        from hope_documents.config import wsgi # noqa: F401 # Import here to trigger side effects

        mock_setdefault.assert_called_once_with(
            "DJANGO_SETTINGS_MODULE", "hope_documents.config.settings"
        )
        mock_get_wsgi_application.assert_called_once()
        # Ensure that wsgi.application is the result of get_wsgi_application
        self.assertEqual(wsgi.application, mock_get_wsgi_application.return_value)