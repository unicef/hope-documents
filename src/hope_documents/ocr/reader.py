import logging

import numpy as np
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

    def try_rotate(self, image: Image) -> str:
        raise NotImplementedError()


class Reader(BaseReader):
    lang = "eng"

    def try_rotate(self, image: Image) -> str:
        highest_avg_conf = -1.0
        best_text = ""  # Variable to store the text from the best rotation

        for angle in [0, 90, 180, 270]:
            if angle == 0:
                rotated_image = image
            else:
                rotated_image = image.rotate(angle, expand=True)

            try:
                data = pytesseract.image_to_data(
                    rotated_image, lang=self.lang, config=self.config, output_type=pytesseract.Output.DICT
                )

                # Get confidences and recognized words
                confidences = [int(c) for i, c in enumerate(data["conf"]) if int(c) != -1 and data["text"][i].strip()]
                recognized_words = [t for t in data["text"] if t.strip()]

                avg_conf = np.mean(confidences) if confidences else 0.0

                # If this angle is better, store its text
                if avg_conf > highest_avg_conf:
                    highest_avg_conf = float(avg_conf)
                    best_text = " ".join(recognized_words)

            except ImportError:
                continue

        return best_text

    def extract(self, image: Image) -> str:
        try:
            text = pytesseract.image_to_string(image, lang=self.lang, config=self.config)
            return "\n".join([line for line in text.splitlines() if line])
        except TesseractError as e:
            raise ExtractionError() from e
