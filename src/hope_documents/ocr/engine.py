from collections.abc import Generator
from dataclasses import dataclass
from functools import cached_property
from pathlib import Path
from typing import Any, TypedDict

from hope_documents.exceptions import InvalidImageError
from hope_documents.ocr.loader import SmartLoader
from hope_documents.ocr.reader import Reader


class ScanInfo(TypedDict):
    filepath: str
    text: str
    error: str


@dataclass
class TSConfig:
    psm: int = 11
    oem: int = 3
    number_only: bool = False
    extra: str = ""

    def __str__(self) -> str:
        cfg = f"--oem {self.oem}  --psm {self.psm} {self.extra}"
        extra = ""
        if self.number_only:
            extra = "tessedit_char_whitelist=0123456789"
        if extra:
            cfg = f"{cfg} -c {extra}"
        return cfg


@dataclass
class CV2Config:
    threshold: int = 128

    def as_dict(self) -> dict[str, Any]:
        return {"threshold": self.threshold}


class Processor:
    def __init__(self, *args: list[str], ts_config: TSConfig, cv2_config: CV2Config) -> None:
        self.filepaths = args
        self.ts_config = str(ts_config)
        self.cv2_config = cv2_config

    @property
    def files(self) -> Generator[str, None, None]:
        for arg in self.filepaths:
            entry = Path(str(arg))
            if entry.is_dir():
                for filename in entry.rglob("*.*"):
                    yield str(filename)
            else:
                yield str(entry)

    @cached_property
    def loader(self) -> SmartLoader:
        return SmartLoader(**self.cv2_config.as_dict())

    @cached_property
    def reader(self) -> Reader:
        return Reader(str(self.ts_config))

    def process(self) -> Generator[ScanInfo]:
        for filepath in self.files:
            ret: ScanInfo = {"filepath": filepath, "text": "", "error": ""}
            try:
                image = self.loader.load(filepath)
                text = self.reader.extract(image)
                ret["text"] = text
            except InvalidImageError as e:
                ret["error"] = f"{e.__class__.__name__}: {str(e)}"
            yield ret
