import base64

from unittest.mock import MagicMock

from PIL import Image as PILImage

from hope_documents.llm.backends import OllamaBackend, OpenAICompatibleBackend


def _small_image() -> PILImage.Image:
    return PILImage.new("RGB", (10, 10), color="white")


def test_ollama_backend_sends_prompt_and_image(monkeypatch):
    fake_response = MagicMock()
    fake_response.message.content = "result"
    fake_client = MagicMock()
    fake_client.chat.return_value = fake_response
    monkeypatch.setattr("hope_documents.llm.backends.ollama.Client", lambda host: fake_client)

    backend = OllamaBackend(host="http://localhost:11434", model="llama3.2-vision")
    result = backend.complete("extract first_name", _small_image())

    assert result == "result"
    _, kwargs = fake_client.chat.call_args
    msg = kwargs["messages"][0]
    assert msg["content"] == "extract first_name"
    assert len(msg["images"]) == 1
    base64.b64decode(msg["images"][0])  # must not raise


def test_openai_compatible_backend_sends_data_url(monkeypatch):
    fake_response = MagicMock()
    fake_response.choices[0].message.content = "openai_result"
    fake_client = MagicMock()
    fake_client.chat.completions.create.return_value = fake_response
    monkeypatch.setattr("hope_documents.llm.backends.openai.OpenAI", lambda **kw: fake_client)

    backend = OpenAICompatibleBackend(base_url="http://localhost:1234", model="llava")
    result = backend.complete("extract first_name", _small_image())

    assert result == "openai_result"
    call_kwargs = fake_client.chat.completions.create.call_args[1]
    content = call_kwargs["messages"][0]["content"]
    image_part = next(p for p in content if p["type"] == "image_url")
    assert image_part["image_url"]["url"].startswith("data:image/png;base64,")
