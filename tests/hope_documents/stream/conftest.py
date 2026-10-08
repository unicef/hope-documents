import base64
import io
from unittest.mock import MagicMock

import pytest
from PIL import Image
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


@pytest.fixture
def image_b64() -> str:
    """A tiny valid PNG, base64-encoded the way Country Workspace sends it."""
    buf = io.BytesIO()
    Image.new("RGB", (80, 50), color="white").save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


@pytest.fixture
def request_payload(image_b64):
    return {
        "correlation_id": "corr-1",
        "rdp_id": 123,
        "batch_id": "batch-1",
        "batch_index": 1,
        "batch_total": 1,
        "documents": [
            {
                "individual_id": 456,
                "content": image_b64,
                "pattern": "ID-987654",
            }
        ],
    }


@pytest.fixture
def pika_args():
    method = MagicMock()
    method.routing_key = "hd.ocr.request"
    return MagicMock(), method, MagicMock()
