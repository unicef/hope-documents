from unittest.mock import patch

from streaming.manager import ChangeManager, initialize_engine
from streaming.utils import check_callback, make_event

from hope_documents.stream.callbacks import handle_event
from hope_documents.stream.publish import publish


def test_handle_event_is_a_valid_callback():
    assert check_callback(handle_event) is True


def test_publish_succeeds_on_console_backend():
    assert publish("ocr.result", {"hello": "hd"}) is True


def test_engine_uses_configured_manager_class(settings):
    manager = initialize_engine(True)
    assert isinstance(manager, ChangeManager)
    assert manager.backend.client_name == settings.STREAMING["CLIENT_NAME"]


def test_hope_documents_queue_uses_binding_keys(settings):
    queues = settings.STREAMING["QUEUES"]
    assert "binding_keys" in queues["hope_documents"]
    assert queues["hope_documents"]["binding_keys"] == ["ocr.request"]
    assert "routing" not in queues["hope_documents"]


@patch("hope_documents.stream.callbacks.process_ocr_batch.delay")
def test_handle_event_enqueues_task_and_does_not_run_ocr(mock_delay, request_payload, pika_args):
    ch, method, properties = pika_args
    body = make_event(request_payload).marshall()

    with patch("hope_documents.stream.ocr.Processor") as mock_processor:
        assert handle_event("hope_documents", ch, method, properties, body) is True

    mock_delay.assert_called_once_with(request_payload)
    mock_processor.assert_not_called()


@patch("hope_documents.stream.callbacks.process_ocr_batch.delay")
def test_handle_event_acks_invalid_payload_without_enqueue(mock_delay, pika_args):
    ch, method, properties = pika_args
    body = make_event({"not": "an ocr request"}).marshall()

    assert handle_event("hope_documents", ch, method, properties, body) is True
    mock_delay.assert_not_called()


@patch("hope_documents.stream.callbacks.process_ocr_batch.delay")
def test_handle_event_acks_malformed_body_without_enqueue(mock_delay, pika_args):
    ch, method, properties = pika_args

    assert handle_event("hope_documents", ch, method, properties, b"not-json") is True
    mock_delay.assert_not_called()


@patch("hope_documents.stream.callbacks.process_ocr_batch.delay")
def test_handle_event_enqueues_empty_documents_batch(mock_delay, request_payload, pika_args):
    ch, method, properties = pika_args
    request_payload["documents"] = []
    body = make_event(request_payload).marshall()

    assert handle_event("hope_documents", ch, method, properties, body) is True
    mock_delay.assert_called_once_with(request_payload)
