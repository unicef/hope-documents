from unittest.mock import MagicMock, call, patch

import pytest

from hope_documents.stream import publish as publish_mod
from hope_documents.stream.publish import OCR_RESULT_ROUTING_KEY, publish
from hope_documents.stream.tasks import OCRResultPublishError, process_ocr_batch, publish_ocr_result


@patch.object(publish_mod, "initialize_engine")
def test_publish_succeeds_on_first_attempt(init):
    manager = MagicMock()
    manager.notify.return_value = True
    init.return_value = manager

    assert publish(OCR_RESULT_ROUTING_KEY, {"ok": True}) is True

    init.assert_called_once_with()
    manager.notify.assert_called_once()


@patch.object(publish_mod, "initialize_engine")
def test_publish_resets_engine_and_retries_after_failure(init):
    stale = MagicMock()
    stale.notify.return_value = False
    fresh = MagicMock()
    fresh.notify.return_value = True
    init.side_effect = [stale, fresh]

    assert publish(OCR_RESULT_ROUTING_KEY, {"ok": True}) is True

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

    assert publish(OCR_RESULT_ROUTING_KEY, {"ok": True}) is False


RESULT = {"correlation_id": "c", "batch_id": "b"}


@patch("hope_documents.stream.tasks.publish_ocr_result.apply_async")
@patch("hope_documents.stream.tasks.publish", return_value=True)
@patch("hope_documents.stream.tasks.run_ocr_batch", return_value=RESULT)
def test_process_ocr_batch_publishes_without_retry(mock_run, mock_publish, mock_retry):
    assert process_ocr_batch({"correlation_id": "c"}) == RESULT

    mock_publish.assert_called_once_with(OCR_RESULT_ROUTING_KEY, RESULT)
    mock_retry.assert_not_called()


@patch("hope_documents.stream.tasks.publish_ocr_result.apply_async")
@patch("hope_documents.stream.tasks.publish", return_value=False)
@patch("hope_documents.stream.tasks.run_ocr_batch", return_value=RESULT)
def test_process_ocr_batch_schedules_delivery_retry_when_publish_fails(mock_run, mock_publish, mock_retry, settings):
    settings.OCR_RESULT_PUBLISH_RETRY_BACKOFF_MAX = 30

    assert process_ocr_batch({"correlation_id": "c"}) == RESULT

    mock_run.assert_called_once()
    mock_retry.assert_called_once()
    assert mock_retry.call_args.kwargs["args"] == [RESULT]
    assert 0 <= mock_retry.call_args.kwargs["countdown"] <= 30


@patch("hope_documents.stream.tasks.publish_ocr_result.apply_async")
@patch("hope_documents.stream.tasks.publish", return_value=False)
@patch("hope_documents.stream.tasks.run_ocr_batch", return_value=RESULT)
def test_process_ocr_batch_raises_when_retries_disabled(mock_run, mock_publish, mock_retry, settings):
    settings.OCR_RESULT_PUBLISH_MAX_RETRIES = 0

    with pytest.raises(OCRResultPublishError, match=f"{OCR_RESULT_ROUTING_KEY}: publish failed"):
        process_ocr_batch({"correlation_id": "c"})
    mock_retry.assert_not_called()


@patch("hope_documents.stream.tasks.run_ocr_batch")
@patch("hope_documents.stream.tasks.publish", side_effect=[False, False, True])
def test_publish_ocr_result_retries_until_published_without_rerunning_ocr(mock_publish, mock_run, settings):
    settings.OCR_RESULT_PUBLISH_MAX_RETRIES = 5

    publish_ocr_result.apply(args=[RESULT]).get()

    assert mock_publish.call_args_list == [call(OCR_RESULT_ROUTING_KEY, RESULT)] * 3
    mock_run.assert_not_called()


@patch("hope_documents.stream.tasks.logger")
@patch("hope_documents.stream.tasks.publish", return_value=False)
def test_publish_ocr_result_gives_up_after_max_retries(mock_publish, mock_logger, settings):
    settings.OCR_RESULT_PUBLISH_MAX_RETRIES = 3

    with pytest.raises(OCRResultPublishError, match="retry=3/3"):
        publish_ocr_result.apply(args=[RESULT]).get()

    assert mock_publish.call_count == 3
    mock_logger.error.assert_called_once()
    assert "retries exhausted" in mock_logger.error.call_args.args[0]
