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

    def build(self, psm: int | None = None) -> str:
        effective_psm = psm if psm is not None else self.psm
        cfg = f"--oem {self.oem}  --psm {effective_psm} {self.extra}"
        if self.number_only:
            cfg = f"{cfg} -c tessedit_char_whitelist=0123456789"
        return cfg

    def __str__(self) -> str:
        return self.build()


class BaseReader:
    def __init__(self, config: TSConfig) -> None:
        logger.debug(config)
        self.config = config

    def extract(self, image: Image, *, psm: int | None = None) -> str:
        raise NotImplementedError()


class Reader(BaseReader):
    lang = "eng"

    def extract(self, image: Image, *, psm: int | None = None) -> str:
        try:
            text = pytesseract.image_to_string(image, lang=self.lang, config=self.config.build(psm), timeout=10)
            return "\n".join([line for line in text.splitlines() if line])
        except (TesseractError, RuntimeError, TimeoutExpired) as e:
            raise ExtractionError() from e
