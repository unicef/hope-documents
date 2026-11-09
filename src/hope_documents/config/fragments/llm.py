import json
import os

LLM_BACKEND: dict | None = json.loads(os.environ.get("HOPE_LLM_BACKEND", "null"))
EXTRACTOR_CHAIN: list[str] = os.environ.get("HOPE_EXTRACTOR_CHAIN", "ocr").split(",")
