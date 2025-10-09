import logging

import pytesseract
from PIL.Image import Image

logger = logging.getLogger(__name__)


class Reader:
    def __init__(self, config: str) -> None:
        logger.debug(config)
        self.config = config

    def extract(self, image: Image) -> str:
        return pytesseract.image_to_string(image, config=self.config)
