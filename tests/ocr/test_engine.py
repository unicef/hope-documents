from pathlib import Path

import pytest

from hope_documents.ocr.engine import CV2Config, MatchMode, Processor, TSConfig
from hope_documents.ocr.loaders import loader_registry

EXPECTATIONS = (
    ## Ita
    ("ita/ts1.png", "RSSMRA98H1OH501W", False),
    ("ita/ts1.png", "ZZZZ", False),
    ("ita/dl1.png", "M01699252K", True),
    ("ita/dl2.png", "AOA000000A", True),
    # ("ita/dl3.png", "AA0000000A", True),
    ("ita/id1.png", "123456", True),
    ("ita/id2.png", "123456", True),
    ## South Sudan
    ("ssd/dl1.png", "25049", True),
    # ("ssd/dl2.png", "00000000", True),
    ("ssd/pp1.png", "M5500000000011", True),
    ("ssd/pp1.png", "M5500000000011", True),
    ## Sudan
    ("sdn/dl1.png", "L03p29892", True),
    ("sdn/pp1.png", "114-8277-2864", True),
    ("sdn/pp2.png", "A0000000000000", True),
)
images_dir = Path(__file__).parent.parent / "images"


# valid_images = [p for p in images_dir.rglob("eng/*") if not p.is_dir() and not p.name.startswith("_")]
# invalid_images = [p for p in images_dir.rglob("*") if not p.is_dir() and p.name.startswith("_")]


@pytest.fixture(params=[{"psm": 11, "oem": 3, "number_only": False}])
def processor(request) -> Processor:
    ts_config = TSConfig(**request.param)
    cv2_config = CV2Config()
    loaders = loader_registry
    return Processor(ts_config, cv2_config, loaders)


@pytest.mark.parametrize(("filename", "text", "found"), EXPECTATIONS)
def test_process(processor, filename, text, found) -> None:
    findings = list(processor.find_text(str(images_dir / filename), text))
    if found:
        assert len(findings) == 1
        assert findings[0].found is found
        assert findings[0].matches[0]["match"]
    else:
        assert not findings


@pytest.mark.parametrize(("filename", "text", "found"), EXPECTATIONS[0:1])
def test_process_all(processor, filename, text, found) -> None:
    findings = list(processor.find_text(str(images_dir / filename), text, mode=MatchMode.ALL))
    if found:
        assert findings
    else:
        assert not any(x.matches for x in findings)


@pytest.mark.parametrize(("target", "distance"), [("MO1699252K", 0)])
def test_process_best(processor, target, distance) -> None:
    findings = list(processor.find_text(str(images_dir / "ita/dl1.png"), target, mode=MatchMode.BEST))
    assert len(findings) == 1
    assert findings[0].found
    assert findings[0].matches[0]["match"]
    assert findings[0].matches[0]["distance"] == distance
