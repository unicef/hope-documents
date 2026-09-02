from unittest.mock import MagicMock, call, patch

import pytest

from hope_documents.stream import publish as publish_mod
from hope_documents.stream.publish import publish
from hope_documents.stream.tasks import process_ocr_batch


@patch.object(publish_mod, "initialize_engine")
def test_publish_succeeds_on_first_attempt(init):
    manager = MagicMock()
    manager.notify.return_value = True
    init.return_value = manager

    assert publish("ocr.result", {"ok": True}) is True

    init.assert_called_once_with()
    manager.notify.assert_called_once()


@patch.object(publish_mod, "initialize_engine")
def test_publish_resets_engine_and_retries_after_failure(init):
    stale = MagicMock()
    stale.notify.return_value = False
    fresh = MagicMock()
    fresh.notify.return_value = True
    init.side_effect = [stale, fresh]

    assert publish("ocr.result", {"ok": True}) is True

    assert init.call_args_list == [call(), call(True)]
    stale.notify.assert_called_once()
    fresh.notify.assert_called_once()


@patch.object(publish_mod, "initialize_engine")
def test_publish_returns_false_when_retry_also_fails(init):
    stale = MagicMock()
    stale.notify.return_value = False
    fresh = MagicMock()
    fresh.notify.return_value = False
    init.side_effect = [stale, fresh]

    assert publish("ocr.result", {"ok": True}) is False


@patch("hope_documents.stream.tasks.publish", return_value=False)
@patch("hope_documents.stream.tasks.run_ocr_batch", return_value={"correlation_id": "c", "batch_id": "b"})
def test_process_ocr_batch_raises_when_publish_fails(mock_run, mock_publish):
    with pytest.raises(RuntimeError, match="ocr.result: publish failed"):
        process_ocr_batch({"correlation_id": "c"})
