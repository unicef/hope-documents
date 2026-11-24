import io
from unittest.mock import MagicMock

import pytest
from PIL import Image
from django.core.files.base import ContentFile
from django.core.files.storage import Storage, storages
from streaming.manager import initialize_engine

CONSOLE_STREAMING = {
    "BROKER_URL": "console://",
    "CLIENT_NAME": "hope-documents-test",
    "MANAGER_CLASS": "streaming.manager.ChangeManager",
    "LISTEN_CALLBACK": "hope_documents.stream.callbacks.handle_event",
    "QUEUES": {
        "ocr_requests": {"binding_keys": ["hd.ocr.request"]},
    },
}


@pytest.fixture(autouse=True)
def streaming_console(settings):
    settings.STREAMING = CONSOLE_STREAMING
    initialize_engine(True)


@pytest.fixture(autouse=True)
def hope_storage(settings, tmp_path) -> Storage:
    settings.STORAGES = {
        **settings.STORAGES,
        "hope": {
            "BACKEND": "django.core.files.storage.FileSystemStorage",
            "OPTIONS": {"location": str(tmp_path / "hope")},
        },
    }
    return storages["hope"]


@pytest.fixture
def image_bytes() -> bytes:
    """A tiny valid PNG."""
    buf = io.BytesIO()
    Image.new("RGB", (80, 50), color="white").save(buf, format="PNG")
    return buf.getvalue()


@pytest.fixture
def image_filename(hope_storage, image_bytes) -> str:
    """The image stored under a key shaped the way Country Workspace uploads it."""
    return hope_storage.save("2024/afghanistan/CP-2024/CW_ind_456_national_id_image.png", ContentFile(image_bytes))


@pytest.fixture
def request_payload(image_filename):
    return {
        "correlation_id": "corr-1",
        "rdp_id": 123,
        "batch_id": "batch-1",
        "batch_index": 1,
        "batch_total": 1,
        "documents": [
            {
                "individual_id": 456,
                "filename": image_filename,
                "pattern": "ID-987654",
            }
        ],
    }


@pytest.fixture
def pika_args():
    method = MagicMock()
    method.routing_key = "hd.ocr.request"
    return MagicMock(), method, MagicMock()
