from collections.abc import Generator
from dataclasses import dataclass
from functools import cached_property
from pathlib import Path
from typing import Any, TypedDict

from hope_documents.exceptions import ExtractionError, InvalidImageError
from hope_documents.ocr.loaders import Loader, loader_registry
from hope_documents.ocr.reader import Reader


class ScanInfo(TypedDict):
    loader: str
    config: str
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


class Scanner:
    def __init__(self, *args: Any) -> None:
        self.filepaths = args

    @property
    def files(self) -> Generator[str, None, None]:
        for arg in self.filepaths:
            entry = Path(str(arg))
            if entry.is_dir():
                for filename in entry.rglob("*.*"):
                    yield str(filename)
            else:
                yield str(entry)


class Processor:
    def __init__(self, ts_config: TSConfig, cv2_config: CV2Config, loaders: list[type[Loader]] | None = None) -> None:
        self.loader_classes = loaders or loader_registry
        self.ts_config = str(ts_config)
        self.cv2_config = cv2_config

    @cached_property
    def loaders(self) -> list[Loader]:
        return [loader(**self.cv2_config.as_dict()) for loader in self.loader_classes]

    @cached_property
    def reader(self) -> Reader:
        return Reader(str(self.ts_config))

    def process(self, filepath: str, full_scan: bool = False) -> Generator[ScanInfo]:
        for loader in self.loaders:
            ret: ScanInfo = {
                "filepath": filepath,
                "text": "",
                "error": "",
                "loader": loader.__class__.__name__,
                "config": str(self.ts_config),
            }
            try:
                image = loader.load(filepath)
                text = self.reader.extract(image)
                ret["text"] = text
            except (InvalidImageError, ExtractionError) as e:
                ret["error"] = f"{e.__class__.__name__}: {str(e)}"
            if full_scan:
                yield ret
            else:
                break
