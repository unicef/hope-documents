from collections.abc import Generator
from dataclasses import dataclass
from enum import Enum
from functools import cached_property
from pathlib import Path
from typing import Any

from hope_documents.exceptions import ExtractionError, InvalidImageError
from hope_documents.ocr.diff import Match, find_similar
from hope_documents.ocr.loaders import Loader, loader_registry
from hope_documents.ocr.reader import BaseReader, Reader
from hope_documents.utils.timeit import Timer, time_it


@dataclass
class ScanEntryInfo:
    def __init__(self, **kwargs: Any) -> None:
        self.loader: str = ""
        self.text: str = ""
        self.error: str = ""
        self.time: Timer | None = None
        for k, v in kwargs.items():
            setattr(self, k, v)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.__dict__!r})"


@dataclass
class SearchInfo(ScanEntryInfo):
    def __init__(self, **kwargs: Any) -> None:
        self.match: Match | None = None
        self.angle: int = 0
        super().__init__(**kwargs)

    @property
    def found(self) -> bool:
        return bool(self.match)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.__dict__!r})"


@dataclass
class ScanInfo:
    def __init__(self, **kwargs: Any) -> None:
        self.iterations: list[SearchInfo] = []
        for k, v in kwargs.items():
            setattr(self, k, v)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.iterations!r})"


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

    def find_text(  # noqa: C901, PLR0913
        self,
        filepath: str,
        target: str,
        mode: MatchMode = MatchMode.FIRST,
        debug: bool = False,
        max_errors: int = 5,
    ) -> Generator[SearchInfo, Any, None]:
        all_matches = []
        self.debug_info = ScanInfo()
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
                    ret.match = find_similar(target, text, max_errors=max_errors)
                ret.time = m
                if debug:
                    self.debug_info.iterations.append(ret)
                if ret.match:
                    match mode:
                        case MatchMode.BEST:
                            all_matches.append(ret)
                        case MatchMode.FIRST:
                            yield ret
                            return
                        case MatchMode.ALL:
                            yield ret
        if mode == MatchMode.BEST:
            yield min(all_matches, key=lambda item: item.match["distance"] if item.match else 0)

    def process(self, filepath: str) -> Generator[ScanEntryInfo]:
        for loader in self.loaders:
            ret = ScanEntryInfo(loader=loader.__class__.__name__)
            try:
                with time_it() as m:
                    image = loader.load(filepath)
                    text = self.reader.extract(image)
                    ret.text = text
                ret.time = m
            except (InvalidImageError, ExtractionError) as e:
                ret.error = f"{e.__class__.__name__}: {str(e)}"
            yield ret
