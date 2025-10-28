import logging
from dataclasses import dataclass
from subprocess import TimeoutExpired
from typing import Any

import pytesseract
from PIL.Image import Image
from pytesseract import TesseractError

from hope_documents.exceptions import ExtractionError

logger = logging.getLogger(__name__)


@dataclass
class TSConfig:
    def __init__(self, **kwargs: Any) -> None:
        self.psm: int = 11
        self.oem: int = 3
        self.number_only: bool = False
        self.extra: str = ""
        for k, v in kwargs.items():
            setattr(self, k, v)

    def __str__(self) -> str:
        cfg = f"--oem {self.oem}  --psm {self.psm} {self.extra}"
        extra = ""
        if self.number_only:
            extra = "tessedit_char_whitelist=0123456789"
        if extra:
            cfg = f"{cfg} -c {extra}"
        return cfg


class BaseReader:
    def __init__(self, config: TSConfig) -> None:
        logger.debug(config)
        self.config = config

    def extract(self, image: Image) -> str:
        raise NotImplementedError()


class Reader(BaseReader):
    lang = "eng"

    def extract(self, image: Image) -> str:
        try:
            text = pytesseract.image_to_string(image, lang=self.lang, config=str(self.config), timeout=10)
            return "\n".join([line for line in text.splitlines() if line])
        except (TesseractError, RuntimeError, TimeoutExpired) as e:
            raise ExtractionError() from e
