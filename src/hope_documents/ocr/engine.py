from collections.abc import Generator
from dataclasses import dataclass
from enum import Enum
from functools import cached_property
from pathlib import Path
from typing import Any

from hope_documents.exceptions import ExtractionError, InvalidImageError
from hope_documents.ocr.diff import find_similar
from hope_documents.ocr.loaders import Loader, loader_registry
from hope_documents.ocr.reader import BaseReader, Reader
from hope_documents.utils.timeit import Timer, time_it


@dataclass
class ScanInfo:
    def __init__(self, **kwargs: Any) -> None:
        self.loader: str = ""
        self.text: str = ""
        self.error: str = ""
        self.time: Timer | None = None
        for k, v in kwargs.items():
            setattr(self, k, v)


@dataclass
class SearchInfo(ScanInfo):
    def __init__(self, **kwargs: Any) -> None:
        self.matches: list[dict[str, str | int]] = []
        self.angle: int = 0
        super().__init__(**kwargs)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.__dict__!r})"

    @property
    def found(self) -> bool:
        return bool(self.matches)


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


class MatchMode(Enum):
    BEST = 1
    FIRST = 2
    ALL = 3

    @classmethod
    def choices(cls) -> tuple[tuple[int, str], ...]:
        return tuple((i.value, i.name) for i in cls)


class Processor:
    def __init__(self, ts_config: TSConfig, cv2_config: CV2Config, loaders: list[type[Loader]] | None = None) -> None:
        self.loader_classes = loaders or loader_registry
        self.ts_config = str(ts_config)
        self.cv2_config = cv2_config

    @cached_property
    def loaders(self) -> list[Loader]:
        return [loader(**self.cv2_config.as_dict()) for loader in self.loader_classes]

    @cached_property
    def reader(self) -> BaseReader:
        return Reader(str(self.ts_config))

    def find_text(
        self, filepath: str, target: str, mode: MatchMode = MatchMode.FIRST
    ) -> Generator[SearchInfo, Any, None]:
        all_matches = []
        for loader in self.loaders:
            for image, angle in loader.rotate(filepath):
                ret = SearchInfo(loader=loader.__class__.__name__)
                ret.angle = angle
                with time_it() as m:
                    try:
                        text = self.reader.extract(image)
                        ret.text = text
                    except (InvalidImageError, ExtractionError) as e:
                        ret.error = f"{e.__class__.__name__}: {str(e)}"
                    ret.matches = find_similar(target, text)
                ret.time = m
                if ret.matches and mode == MatchMode.FIRST:
                    yield ret
                    return
                elif mode == MatchMode.ALL:
                    yield ret
                else:
                    all_matches.append(ret)
        if mode == MatchMode.BEST:
            entries_with_matches = [info for info in all_matches if info.matches]
            if entries_with_matches:
                yield min(entries_with_matches, key=lambda item: item.matches[0]["distance"])
            else:
                yield SearchInfo()

    def process(self, filepath: str) -> Generator[ScanInfo]:
        for loader in self.loaders:
            ret = ScanInfo(loader=loader.__class__.__name__)
            try:
                with time_it() as m:
                    image = loader.load(filepath)
                    text = self.reader.extract(image)
                    ret.text = text
                ret.time = m
            except (InvalidImageError, ExtractionError) as e:
                ret.error = f"{e.__class__.__name__}: {str(e)}"
            yield ret
