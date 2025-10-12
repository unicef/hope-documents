from pathlib import Path
from unittest import mock

import pytest

from hope_documents.ocr.diff import find_similar1, find_similar2
from hope_documents.ocr.engine import CV2Config, MatchMode, Processor, SearchInfo, TSConfig
from hope_documents.ocr.loaders import loader_registry

FAILURES = (
    ("ita/dl3.png", "AA0000000A", False, MatchMode.FIRST),  # does not work
    ("ssd/dl2.png", "00000000", False, MatchMode.FIRST),  # does not work
    ("swe/id1.png", "820021", True, MatchMode.FIRST),
)

EXPECTATIONS = (
    ## Ita
    ("ita/ts1.png", "RSSMRA98H1OH501W", False, MatchMode.FIRST),
    ("ita/dl1.png", "M01699252K", True, MatchMode.FIRST),
    ("ita/dl2.png", "AOA000000A", True, MatchMode.FIRST),
    ("ita/id1.png", "123456", True, MatchMode.FIRST),
    ("ita/id2.png", "123456", True, MatchMode.FIRST),
    ## South Sudan
    ("ssd/dl1.png", "25049", True, MatchMode.FIRST),
    ("ssd/pp1.png", "M5500000000011", True, MatchMode.FIRST),
    ("ssd/pp1.png", "M5500000000011", True, MatchMode.FIRST),
    ## Sudan
    ("sdn/dl1.png", "L03p29892", True, MatchMode.FIRST),
    ("sdn/pp1.png", "114-8277-2864", True, MatchMode.FIRST),
    ("sdn/pp2.png", "A0000000000000", True, MatchMode.FIRST),
    ## Slovenia
    ("slo/id1.png", "XX024051", True, MatchMode.FIRST),
    ("slo/id1.png", "1111111111", True, MatchMode.FIRST),
    ("slo/id1.png", "199030", True, MatchMode.FIRST),
    ## South Africa
    ("zaf/pp1.png", "3908200125087", True, MatchMode.FIRST),
    ("zaf/pp2.png", "8001014999082", True, MatchMode.FIRST),
)
images_dir = Path(__file__).parent.parent / "images"
private_dir = Path(__file__).parent.parent.parent / "DATA"

EX = (
    ("sdn/1726385754342.jpg", "46145701702", True, 0),
    ("sdn/1726387495025.jpg", "18382359459", True, 0),
    ("sdn/1726387964049.jpg", "183-0725569-6", True, 2),
    #    ("sdn/1726388962876.jpg", "183-9035596-7", True, 0),
    ("sdn/1726389526210.jpg", "183-3361370-3", True, 4),
    ("sdn/1726389733925.jpg", "P11508758", True, 1.0),
    ("sdn/1726389733925.jpg", "18324671053", True, 1.0),
    ("sdn/1726389873575.jpg", "114 6450 8515", True, 1.0),
    ("sdn/1726390666456.jpg", "1835074373-2", True, 1.0),
    ("sdn/1726393829640.jpg", "3-1382243-120", True, 4.0),
    ("sdn/1726406159721.jpg", "1199-7738-501", True, 0),
    ("sdn/1726406159721.jpg", "11997738501", True, 0),
    ("sdn/1726406159721.jpg", "119 977 38501", True, 0),
)


@pytest.fixture(params=[{"psm": 11, "oem": 3, "number_only": False}])
def processor(request) -> Processor:
    ts_config = TSConfig(**request.param)
    cv2_config = CV2Config()
    loaders = loader_registry
    return Processor(ts_config, cv2_config, loaders)


@pytest.mark.parametrize(("filename", "text", "found", "mode"), EXPECTATIONS)
def test_search_text(processor, filename, text, found, mode) -> None:
    findings = list(processor.find_text(str(images_dir / filename), text, mode=mode, debug=True))
    if found:
        assert len(findings) == 1
        assert findings[0].found is found
        assert findings[0].matches[0]["match"]
    else:
        assert not findings


@pytest.mark.parametrize("mode", [MatchMode.ALL, MatchMode.FIRST, MatchMode.BEST])
@pytest.mark.parametrize("impl", [find_similar1, find_similar2])
@pytest.mark.parametrize(("target", "distance"), [("MO1699252K", 0)])
def test_process(processor, target, distance, impl, mode) -> None:
    with mock.patch("hope_documents.ocr.diff.find_similar", impl):
        findings = list(processor.find_text(str(images_dir / "ita/dl1.png"), target, mode=mode))
        assert len(findings) >= 1
        info: SearchInfo = findings[0]
        match = info.matches[0]
        assert info.found
        assert match["distance"] == distance, (
            f"Diff should be {distance}. Got {match['distance']} ({target} != {match['match']})"
        )


@pytest.mark.skipif("not private_dir.exists()", reason=f"{private_dir} does not exist.")
@pytest.mark.parametrize(("filename", "text", "found", "distance"), EX)
def test_search_protected(processor, filename, text, found, distance) -> None:
    findings = list(processor.find_text(str(private_dir / filename), text))
    if found:
        assert len(findings) == 1
        info: SearchInfo = findings[0]
        match = info.matches[0]
        assert info.found
        assert match["distance"] == distance, (
            f"Diff should be {distance}. Got {match['distance']} ({text} != {match['match']})"
        )
    else:
        assert not findings
