import json
import os

from django.core.exceptions import ImproperlyConfigured

_raw = os.environ.get("HOPE_LLM_BACKEND")
if _raw is None:
    LLM_BACKEND: dict | None = None
else:
    try:
        _parsed = json.loads(_raw)
    except json.JSONDecodeError as exc:
        raise ImproperlyConfigured(f"HOPE_LLM_BACKEND is not valid JSON: {exc}") from exc
    if _parsed is not None and not isinstance(_parsed, dict):
        raise ImproperlyConfigured(f"HOPE_LLM_BACKEND must be a JSON object or null, got {type(_parsed).__name__}")
    LLM_BACKEND = _parsed

EXTRACTOR_CHAIN: list[str] = [s.strip() for s in os.environ.get("HOPE_EXTRACTOR_CHAIN", "ocr").split(",")]
