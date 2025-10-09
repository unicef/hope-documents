import logging

import pytesseract
from PIL.Image import Image
from pytesseract import TesseractError

from hope_documents.exceptions import ExtractionError

logger = logging.getLogger(__name__)


class Reader:
    def __init__(self, config: str) -> None:
        logger.debug(config)
        self.config = config

    def extract(self, image: Image) -> str:
        try:
            text = pytesseract.image_to_string(image, lang="eng", config=self.config)
            return "\n".join([line for line in text.splitlines() if line])
        except TesseractError as e:
            raise ExtractionError() from e
