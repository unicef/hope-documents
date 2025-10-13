from pathlib import Path
from unittest import mock

import PIL.Image
import pytest
from django.core.files.uploadedfile import UploadedFile
from django.template import Context, Template

from hope_documents.ocr.diff import find_similar1, find_similar2
from hope_documents.ocr.engine import CV2Config, MatchMode, Processor, SearchInfo, TSConfig
from hope_documents.ocr.loaders import loader_registry
from hope_documents.utils.image import get_image_base64

FAILURES = ()

EXPECTATIONS = (
    ("and/pp1.png", "PP9500063", True, 0),
    ("arg/id1.png", "99.999.999", True, 0),
    ("bhr/pp1.png", "80000000", True, 0),
    ("chi/pp1.png", "RX0006664", True, 0),
    ("chn/pp1.png", "888800088", True, 0),
    ("deu/dp1.png", "CZ638HW3P", True, 0),
    ("deu/dp2.png", "CZ638HW3P", True, 0),
    ("deu/dr1.png", "Z021AB37X13", True, 0),
    ("eri/pp1.png", "K0064640", True, 0),
    ("fin/dr1.png", "0104044898VV1", True, 0),
    ("hun/id1.png", "012345", True, 0),
    ("isr/id1.png", "1 2345678 9", True, 0),
    ("isr/id1.png", "123456789", True, 0),
    ("onu/dp1.png", "SUNJ00000", True, 0),
    ("phl/pp1.png", "P0000000A", True, 0),
    ("pol/pp1.png", "ZP7202173", True, 0),
    ("pse/id1.png", "924445117", True, 0),
    ("pse/id2.png", "0 0000000 0", True, 0),
    ("pse/id3.png", "0 0000000 0", True, 0),
    ("pse/pp1.png", "ROPOSH.COM", True, 0),
    ("pse/pp1.png", "0000000", True, 0),
    ("rou/id1.png", "SP1234694", False, 0),
    ## Ita
    ("ita/ts1.png", "RSSMRA98H1OH501W", False, 0),
    # ("ita/dl3.png", "AA0000000A", True, 5.0),  # does not work
    # ("ssd/dl2.png", "00000000", True, 5.0),  # does not work
    ("swe/id1.png", "820021", True, 0),
    ("ita/dl1.png", "M01699252K", True, 0),
    ("ita/dl2.png", "AOA000000A", True, 0),
    ("ita/id1.png", "123456", True, 0),
    ("ita/id2.png", "123456", True, 0),
    ## South Sudan
    ("ssd/dl1.png", "25049", True, 0),
    ("ssd/pp1.png", "M5500000000011", True, 0),
    ("ssd/pp1.png", "M5500000000011", True, 0),
    ## Sudan
    ("sdn/dl1.png", "L03p29892", True, 0),
    ("sdn/pp1.png", "114-8277-2864", True, 0),
    ("sdn/pp2.png", "A0000000000000", True, 0),
    ## Slovenia
    ("slo/id1.png", "XX024051", True, 0),
    ("slo/id1.png", "1111111111", True, 0),
    ("slo/id1.png", "199030", True, 0),
    ## South Africa
    ("zaf/pp1.png", "3908200125087", True, 0),
    ("zaf/pp2.png", "8001014999082", True, 0),
)

EX = (
    ("sdn/1726385754342.jpg", "46145701702", True, 0),
    ("sdn/1726387495025.jpg", "18382359459", True, 0),
    ("sdn/1726387964049.jpg", "183-0725569-6", True, 2),
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
images_dir = Path(__file__).parent.parent / "images"
private_dir = Path(__file__).parent.parent.parent / "DATA"


@pytest.fixture(params=[{"psm": 11, "oem": 3, "number_only": False}])
def processor(request) -> Processor:
    ts_config = TSConfig(**request.param)
    cv2_config = CV2Config()
    loaders = loader_registry
    return Processor(ts_config, cv2_config, loaders)


@pytest.mark.parametrize(("filename", "text", "found", "mode"), EXPECTATIONS)
def test_search_text(processor, filename, text, found, mode) -> None:
    findings = list(processor.find_text(str(images_dir / filename), text, mode=MatchMode.FIRST, debug=True))
    if found:
        assert len(findings) == 1
        assert findings[0].found is found
        assert findings[0].match
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
        match = info.match
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
        assert info.found
        assert info.match["distance"] == distance, (
            f"Diff should be {distance}. Got {info.match['distance']} ({text} != {info.match['match']})"
        )
    else:
        assert not findings


@pytest.mark.skipif("not private_dir.exists()", reason=f"{private_dir} does not exist.")
def test_create_report(processor):
    report = Path(__file__).parent.parent.parent / ".report.html"

    def get_class(s: SearchInfo):
        if s.match:
            return f"d{int(s.match['distance'])}"
        return "d5"

    all_files = []
    all_files.extend([(str(private_dir / filename), a, b, c) for filename, a, b, c in EX])
    all_files.extend([(str(images_dir / filename), a, b, c) for filename, a, b, c in EXPECTATIONS])
    lines = []
    errors = []
    warnings = []
    success = []
    for target, text, __, __ in all_files:
        filename = Path(target).name
        image = PIL.Image.open(target)
        width, height = image.size
        with open(target, "rb") as fi:
            base64 = get_image_base64(UploadedFile(fi, name=filename))
        for mode in [MatchMode.FIRST]:
            findings = list(processor.find_text(target, text, mode=mode, debug=True))
            if findings and findings[0].match["distance"] == 0:
                success.append(findings)
                si = findings[0]
            elif findings and findings[0].match["distance"] > 0:
                warnings.append(findings)
                si = findings[0]
            else:
                errors.append(findings)
                si = SearchInfo()
            lines.append(
                {
                    "filename": filename,
                    "search_text": text,
                    "image": base64,
                    "info": f"{int(width)}x{int(height)}",
                    "si": si,
                    "class": get_class(si),
                }
            )
    template = Template((Path(__file__).parent / "template.html").read_text(encoding="utf-8"))
    with Path(report).open("w", encoding="utf-8") as f:
        f.write(template.render(Context({"lines": lines, "errors": errors, "warnings": warnings, "success": success})))
