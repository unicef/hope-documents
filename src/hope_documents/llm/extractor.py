import json
import logging
import re

from constance import config
from PIL import Image

from hope_documents.archive.region import BoundingBox
from hope_documents.llm.backends import LLMBackend
from hope_documents.llm.prompt import PromptBuilder

logger = logging.getLogger(__name__)

_FENCE_RE = re.compile(r"```(?:json)?\n?(.*?)```", re.DOTALL)


class LLMAttributeExtractor:
    def __init__(self, backend: LLMBackend) -> None:
        self.backend = backend

    def extract_attribute(
        self,
        image: Image.Image,
        attribute_name: str,
        region: BoundingBox | None,
    ) -> str:
        builder = (
            PromptBuilder()
            .with_role()
            .with_field_hint(attribute_name)
            .with_rules()
            .with_output_format()
        )
        if region is not None:
            builder = builder.with_region_hint(region, image.size)
        prompt = builder.build()

        try:
            raw = self.backend.complete(prompt, image)
        except Exception:
            logger.warning("LLM backend failed for attribute '%s'", attribute_name, exc_info=True)
            return ""

        stripped = _FENCE_RE.sub(r"\1", raw).strip()

        try:
            parsed = json.loads(stripped)
        except json.JSONDecodeError:
            logger.warning("LLM returned non-JSON for attribute '%s': %r", attribute_name, stripped)
            return ""

        if parsed.get("confidence", 0) < config.LLM_CONFIDENCE_THRESHOLD:
            return ""

        value = parsed.get("value")
        if value is None:
            return ""
        return str(value).strip()
