import base64
import io
from typing import Protocol, runtime_checkable

import ollama
import openai
from PIL import Image


@runtime_checkable
class LLMBackend(Protocol):
    def complete(self, prompt: str, image: Image.Image) -> str: ...  # pragma: no cover


def _b64_encode_image(image: Image.Image) -> str:
    """Return the image as a base64-encoded PNG string."""
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


class OllamaBackend:
    def __init__(
        self,
        host: str = "http://localhost:11434",
        model: str = "llama3.2-vision",
        max_tokens: int = 256,
    ) -> None:
        self.host = host
        self.model = model
        self.max_tokens = max_tokens
        self._client = ollama.Client(host=host)

    def complete(self, prompt: str, image: Image.Image) -> str:
        buf = io.BytesIO()
        image.save(buf, format="PNG")
        response = self._client.chat(
            model=self.model,
            messages=[{"role": "user", "content": prompt, "images": [buf.getvalue()]}],
            options={"num_predict": self.max_tokens},
        )
        return response.message.content


class OpenAICompatibleBackend:
    def __init__(self, base_url: str, model: str, api_key: str = "ollama", max_tokens: int = 256) -> None:
        self.base_url = base_url
        self.model = model
        self.api_key = api_key
        self.max_tokens = max_tokens
        self._client = openai.OpenAI(base_url=base_url, api_key=api_key)

    def complete(self, prompt: str, image: Image.Image) -> str:
        b64 = _b64_encode_image(image)
        response = self._client.chat.completions.create(
            model=self.model,
            max_tokens=self.max_tokens,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
                    ],
                }
            ],
        )
        return response.choices[0].message.content
