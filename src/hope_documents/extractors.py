from typing import Protocol, runtime_checkable

from PIL import Image

from hope_ocr.archive.region import BoundingBox
from hope_ocr.exceptions import ExtractionError, InvalidImageError
from hope_ocr.ocr.engine import Processor


@runtime_checkable
class AttributeExtractor(Protocol):
    def extract_attribute(
        self,
        image: Image.Image,
        attribute_name: str,
        region: BoundingBox | None,
    ) -> str: ...


class OCRAttributeExtractor:
    """Extracts attribute values using OCR.

    Regions are treated as hints: the crop is tried first, but if it returns
    nothing (misaligned box, low-res crop) the extractor falls back to a
    full-image fuzzy search. This fallback pattern is intentional — the same
    interface will be used by future LLM-based extractors.
    """

    def __init__(self, processor: Processor) -> None:
        self.processor = processor

    def extract_attribute(
        self,
        image: Image.Image,
        attribute_name: str,
        region: BoundingBox | None,
    ) -> str:
        if region:
            try:
                cropped = image.crop(
                    (
                        int(region.top_left.x),
                        int(region.top_left.y),
                        int(region.bottom_right.x),
                        int(region.bottom_right.y),
                    )
                )
                value = self.processor.reader.extract(cropped).strip()
            except (ExtractionError, InvalidImageError, OSError, ValueError):
                value = ""
            if value:
                return value
        text, _ = self.processor.find_single(image, attribute_name)
        return text.strip()
