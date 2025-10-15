import logging
from collections.abc import Generator, Iterable
from dataclasses import dataclass
from enum import Enum
from functools import cached_property
from pathlib import Path
from typing import Any

from hope_documents.exceptions import ExtractionError, InvalidImageError
from hope_documents.ocr.diff import Match, find_similar
from hope_documents.ocr.loaders import (
    BWLoader,
    CV2Loader,
    EnhancedLoader,
    ImprovedLoader,
    Loader,
    PILLoader,
    SmartLoader,
)
from hope_documents.ocr.reader import BaseReader, Reader
from hope_documents.utils.timeit import format_elapsed_time, time_it

logger = logging.getLogger(__name__)

SEARCH_TEST_PATTERN = "||doc-test||"


@dataclass
class ScanEntryInfo:
    __slots__ = ["loader", "text", "error", "time"]

    def __init__(self, *, loader: str) -> None:
        self.loader = loader
        self.text: str = ""
        self.error: str = ""
        self.time: str = ""

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.loader})"


@dataclass
class SearchInfo(ScanEntryInfo):
    __slots__ = ["loader", "text", "error", "time", "match", "angle", "iterations"]

    def __init__(
        self,
        *,
        loader: str,
        match: Match | None = None,
        angle: int = 0,
    ) -> None:
        self.match = match
        self.angle = angle
        self.iterations = []
        super().__init__(loader=loader)

    @property
    def found(self) -> bool:
        return bool(self.match)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.loader}):{self.match!r}:{self.angle!r}:{self.time!r}"


@dataclass
class ScanInfo:
    def __init__(self) -> None:
        self.iterations: list[SearchInfo] = []

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
        self.loader_classes = loaders or [
            Loader,
            PILLoader,
            EnhancedLoader,
            CV2Loader,
            SmartLoader,
            BWLoader,
            ImprovedLoader,
        ]
        self.ts_config = str(ts_config)
        self.cv2_config = cv2_config

    @cached_property
    def loaders(self) -> list[Loader]:
        return [loader(**self.cv2_config.as_dict()) for loader in self.loader_classes]

    @cached_property
    def reader(self) -> BaseReader:
        return Reader(str(self.ts_config))

    def find_text(  # noqa: C901, PLR0913, PLR0912
        self,
        filepath: str,
        target: str,
        mode: MatchMode = MatchMode.FIRST,
        debug: bool = False,
        max_errors: int = 5,
        rotations: Iterable[int] = (270, 0),
    ) -> Generator[SearchInfo, Any, None]:
        all_matches = []
        self.debug_info = ScanInfo()
        iterations = []
        with time_it() as timer1:
            for loader in self.loaders:
                stop_loader_iteration = False
                loader.rotations = rotations
                iterations.append({"loader": loader.__class__.__name__, "angles": []})
                for image, angle in loader.rotate(filepath):
                    ret = SearchInfo(loader=loader.__class__.__name__, angle=angle)
                    try:
                        text = self.reader.extract(image)
                        ret.text = text
                        logger.debug(f"Loader {loader} angle {angle}: text found {text.replace('\n', ' | ')}")
                        if text != SEARCH_TEST_PATTERN:
                            ret.match = find_similar(target, text, max_distance=max_errors)
                        logger.debug(f"Loader {loader} angle {angle}: searching for `{target}`: {ret.match}")
                    except (InvalidImageError, ExtractionError) as e:
                        ret.error = f"{e.__class__.__name__}: {str(e)}"
                    iterations[-1]["angles"].append(ret)
                    ret.iterations = iterations
                    ret.time = format_elapsed_time(timer1.get_partial())
                    if debug:
                        self.debug_info.iterations.append(ret)
                    if ret.match:
                        match mode:
                            case MatchMode.BEST:
                                all_matches.append(ret)
                                if ret.match.distance == 0.0:
                                    stop_loader_iteration = True
                                    break
                            case MatchMode.FIRST:
                                yield ret
                                return
                            case MatchMode.ALL:
                                yield ret

                if stop_loader_iteration:
                    break
        if mode == MatchMode.BEST and all_matches:
            best_match = min(all_matches, key=lambda item: item.match.distance if item.match else 99999)
            best_match.time = format_elapsed_time(timer1.get_partial())
            yield best_match
        elif target == SEARCH_TEST_PATTERN and ret:
            yield ret

    def process(self, filepath: str, rotate: int = 0) -> Generator[ScanEntryInfo]:
        for loader in self.loaders:
            ret = ScanEntryInfo(loader=loader.__class__.__name__)
            try:
                with time_it() as m:
                    image = loader.load(filepath)
                    if rotate:
                        image = image.rotate(rotate, expand=True)
                    text = self.reader.extract(image)
                    ret.text = text
                ret.time = m
            except (InvalidImageError, ExtractionError) as e:
                ret.error = f"{e.__class__.__name__}: {str(e)}"
            yield ret
