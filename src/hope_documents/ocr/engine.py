import logging
from collections.abc import Generator, Sequence
from dataclasses import dataclass
from enum import Enum
from functools import cached_property
from pathlib import Path
from typing import Any

from PIL import Image

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
from hope_documents.ocr.reader import BaseReader, Reader, TSConfig
from hope_documents.utils.timeit import format_elapsed_time, time_it

logger = logging.getLogger(__name__)

SEARCH_TEST_PATTERN = "SEARCH_TEST_PATTERN"


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
    __slots__ = ["loader", "text", "error", "time", "match", "angle", "iterations", "psm", "attempts"]

    def __init__(
        self,
        *,
        loader: str,
        match: Match | None = None,
        angle: int = 0,
        psm: int = 11,
        attempts: int = 0,
    ) -> None:
        self.match = match
        self.angle = angle
        self.psm = psm
        self.attempts = attempts
        self.iterations: list[dict[str, Any]] = []
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
class CV2Config:
    def __init__(self, threshold: int = 120) -> None:
        self.threshold = threshold

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
        self.ts_config = ts_config
        self.cv2_config = cv2_config

    @cached_property
    def loaders(self) -> list[Loader]:
        return [loader(**self.cv2_config.as_dict()) for loader in self.loader_classes]

    @cached_property
    def reader(self) -> BaseReader:
        return Reader(self.ts_config)

    def find_single(self, image: Image.Image, target: str, max_errors: int = 5) -> tuple[str, Match | None]:
        text = self.reader.extract(image)
        try:
            match = find_similar(target, text, max_distance=max_errors)
        except (InvalidImageError, ExtractionError):
            match = None
        return text, match

    def find_text(  # noqa: C901, PLR0913, PLR0912
        self,
        original: Image.Image,
        target: str,
        mode: MatchMode = MatchMode.FIRST,
        debug: bool = False,
        max_errors: int = 5,
        rotations: Sequence[int] = (270, 0),
        psms: Sequence[int] = (11, 6),
    ) -> Generator[SearchInfo, Any, None]:
        all_matches = []
        self.debug_info = ScanInfo()
        iterations: list[dict[str, Any]] = []
        attempts = 0
        with time_it() as timer1:
            for loader in self.loaders:
                for psm in psms:
                    stop_loader_iteration = False
                    loader.rotations = rotations
                    iterations.append({"loader": loader.__class__.__name__, "angles": []})
                    for image, angle in loader.rotate(original):
                        attempts += 1
                        ret = SearchInfo(loader=loader.__class__.__name__, angle=angle, psm=psm, attempts=attempts)
                        self.reader.config.psm = ret.psm
                        try:
                            ret.text, ret.match = self.find_single(image, target, max_errors=max_errors)
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
                if stop_loader_iteration:
                    break
        if mode == MatchMode.BEST and all_matches:
            best_match = min(all_matches, key=lambda item: item.match.distance if item.match else 99999)
            best_match.time = format_elapsed_time(timer1.get_partial())
            best_match.attempts = attempts
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
                ret.time = m.human
            except (InvalidImageError, ExtractionError) as e:
                ret.error = f"{e.__class__.__name__}: {str(e)}"
            yield ret
