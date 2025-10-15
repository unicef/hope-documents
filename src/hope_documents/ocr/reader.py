import logging

import pytesseract
from PIL.Image import Image
from pytesseract import TesseractError

from hope_documents.exceptions import ExtractionError

logger = logging.getLogger(__name__)


class BaseReader:
    def __init__(self, config: str) -> None:
        logger.debug(config)
        self.config = config

    def extract(self, image: Image) -> str:
        raise NotImplementedError()


class Reader(BaseReader):
    lang = "eng"

    def extract(self, image: Image) -> str:
        try:
            text = pytesseract.image_to_string(image, lang=self.lang, config=self.config, timeout=5)
            return "\n".join([line for line in text.splitlines() if line])
        except (TesseractError, RuntimeError) as e:
            raise ExtractionError() from e
