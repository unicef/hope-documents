from pathlib import Path

import PIL.Image
import pytest
from django.core.files.uploadedfile import UploadedFile
from django.template import Context, Template
from humanize import naturalsize

from hope_documents.ocr.engine import SEARCH_TEST_PATTERN, CV2Config, MatchMode, Processor, SearchInfo, TSConfig
from hope_documents.utils.image import get_image_base64
from hope_documents.utils.timeit import time_it

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
    ("fin/dr1.png", "010404A898V", True, 0),
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
    ("sdn/1726389733925.jpg", "18324671053", True, 1.0),
    ("sdn/1726389733925.jpg", "P11508758", True, 1.0),
    ("sdn/1726389873575.jpg", "114 6450 8515", True, 0),
    ("sdn/1726390666456.jpg", "1835074373-2", True, 1.0),
    ("sdn/1726393399432.jpg", "183-3095388-3", True, 0),
    ("sdn/1726393829640.jpg", "120-1382243-3", True, 0),
    ("sdn/1726394343757.jpg", "11400016482", True, 0),
    ("sdn/1726392186732.jpg", "233-640-1601-2", True, 0),
    ("sdn/1726397518779.jpg", "18-1962-6805", False, 0),
    ("sdn/1726398123018.jpg", "182-1423797-8", True, 3),
    ("sdn/1726404604129.jpg", "183-2858775-9", True, 1),
    ("sdn/1726406159721.jpg", "119 977 38501", True, 0),
    ("sdn/1726406159721.jpg", "1199-7738-501", True, 0),
    ("sdn/1726406159721.jpg", "11997738501", True, 0),
    ("sdn/1726408027541.jpg", "119-15843829", True, 0),
    ("sdn/1726408287344.jpg", SEARCH_TEST_PATTERN, False, 0),
    ("sdn/1726410665866.jpg", SEARCH_TEST_PATTERN, False, 0),
    ("ids/09ab460cf31ea574112a9f50471ff840_qsz2bVhd2893d12-91a4-43fa-8f3c-cbbd532a73ef.jpg", "", False, 0),
    ("ids/1695378272701ffb80c9f-ac88-43e8-bd1b-ab94f4e4ed07.jpg", "A35866731", True, 2),
    ("ids/1708326284259_DzgUHmo.jpg", "A34356968", False, 0),
    ("ids/1709210991456.jpg", "A34431478", False, 0),
    ("ids/1709466917483.jpg", "A34471874", False, 0),
    ("ids/1725804251394_H8NANg0.jpg", "0049626-9476539", False, 0),
    ("ids/1732601511603.jpg", "A37643339", False, 0),
    ("ids/1732634244927.jpg", "A37901088", True, 0),
    ("ids/1732701760334.jpg", "A37336750", True, 0),
    ("ids/1732869785677.jpg", "A31596326", True, 0),
    ("ids/1734436035073.jpg", "90150042212294", True, 1),
    ("ids/1742211725634.jpg", "A69181107", False, 0),
    ("ids/1744179883031.jpg", "A37769091", True, 1),
    ("ids/1752588225101.jpg", "A37166805", False, 0),
    ("ids/1752668706385.jpg", "A36765968", True, 1),
    ("ids/1756118027878.jpg", SEARCH_TEST_PATTERN, False, 0),
    ("ids/340480fffdd06c-17d2-4390-bba9-962a70f448ad.jpg", "340480", True, 1),
    ("ids/3d3d1edb5d9455ba881a831f6a6056bb_HloRzc2fd3695e5-6c9e-4d01-8d12-96e3e45db32a.jpg", "014453", True, 1),
    ("ids/47d3c05134af2b80ef66ba6ccca84ec0f8d04fa4-d770-433b-8132-1b5305cc8928.jpg", "194853", True, 0),
    ("ids/569a71b1572d0e74a9e086c48d31abe3_alE4aRb013e48e0-89a0-45a6-8eff-c32e32fbbe37.jpg", "106296", True, 3),
    ("ids/5a35c4374a5ce22fb564297d31d6caf8_b9AHRd9fefb02a2-92da-412c-ab94-3d7de457ae79.jpg", "055206", True, 0),
    ("ids/76e44f3a93ce0bec7939f0c8062f62f9_W6yGYq2fed40485-7e24-4806-ad81-4d3d9e874fc0.jpg", "105560", True, 3),
    ("ids/7720859e1fd2ef78e17d0a85ba2ba4d8_WW8w3uFfff805c7-624b-494e-a553-14779b9ebdaa.jpg", "985463360V", False, 0),
    ("ids/8f84d138b2ddcf523753f6640d1a4714_qRhvdMKd2379578-be9d-4279-a5c9-bdcf234eb6f2.jpg", "2/145/287/2017", True, 0),
    ("ids/a7492b45a11080d101c0f3e2fe89ebe1fffdee50-01bf-467e-8352-7230beb0c84b.jpg", "324475", True, 4),
    ("ids/abdea691a9d133dbe1c51677308af400fff56a4d-4263-4f7a-8688-b37073645fd1.jpg", "931403257V", False, 0),
    ("ids/cbdd4f2ae21ac985432f9b9525e7ca2dfff8c75b-2f86-43cb-884b-09ac837fe073.jpg", "906381656V", False, 0),
    ("ids/cf35ee75bc24486c43c49ec45d25af31f927bcff-9b0f-45e6-aa68-4872c9fe11ef.jpg", "206802", True, 2),
    ("ids/d10549d9c350ba7d1aac7140757ee029ffffda70-418c-4f27-9bc7-d3f20f21b1b0.jpg", "1-0726-01-2456-7", True, 0),
    ("ids/ef7acbc80cdf9125a69edeeeb21b9f03_xjfC5DY024bedd7-54ac-4370-b04a-8b4e8f76422b.jpg", "129249", True, 4),
    (
        "ids/ONLY_PICTURE_50383c8c-2852-4354-9781-d834e1cbdfa0fffe47e8-856d-4e5f-b832-49bbde9f795a.jpg",
        "445010",
        True,
        3,
    ),
)
images_dir = Path(__file__).parent.parent / "images"
private_dir = Path(__file__).parent.parent.parent / "DATA"


@pytest.fixture(params=[{"psm": 11, "oem": 3, "number_only": False}])
def processor(request) -> Processor:
    ts_config = TSConfig(**request.param)
    cv2_config = CV2Config()
    return Processor(ts_config, cv2_config)


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
@pytest.mark.parametrize(("target", "distance"), [("MO1699252K", 0)])
def test_process(processor, target, distance, mode) -> None:
    if target.isdigit():
        processor.ts_config.number_only = True

    findings = list(processor.find_text(str(images_dir / "ita/dl1.png"), target, mode=mode))
    assert len(findings) >= 1
    info: SearchInfo = findings[0]
    match = info.match
    assert info.found
    assert match.distance == distance, f"Diff should be {distance}. Got {match.distance} ({target} != {match.text})"


@pytest.mark.skipif("not private_dir.exists()", reason=f"{private_dir} does not exist.")
@pytest.mark.parametrize(("filename", "text", "found", "distance"), EX)
@pytest.mark.xdist_group("g1")
def test_search_protected(processor, filename, text, found, distance) -> None:
    findings = list(processor.find_text(str(private_dir / filename), text, mode=MatchMode.BEST))
    if found:
        assert len(findings) == 1
        info: SearchInfo = findings[0]
        assert info.found
        assert info.match.distance == distance, (
            f"Diff should be {distance}. Got {info.match.distance} ({text} != {info.match.text})"
        )
    elif text == SEARCH_TEST_PATTERN:
        assert len(findings) == 1
        info: SearchInfo = findings[0]
        assert not info.found
    else:
        assert not findings


@pytest.mark.report
@pytest.mark.skipif("not private_dir.exists()", reason=f"{private_dir} does not exist.")
@pytest.mark.parametrize("mode", [MatchMode.FIRST, MatchMode.BEST])
def test_create_report(processor, mode, caplog):
    def get_class(s: SearchInfo):
        if s.match:
            return f"d{int(s.match.distance)}"
        return "d5"

    all_files = []
    all_files.extend([(str(private_dir / filename), a, b, c) for filename, a, b, c in EX])
    all_files.extend([(str(images_dir / filename), a, b, c) for filename, a, b, c in EXPECTATIONS])
    all_files = all_files[:]
    lines = []
    errors = []
    warnings = []
    success = []
    with time_it() as m:
        for target, text, __, __ in all_files:
            filename = Path(target).name
            size = Path(target).stat().st_size / 1024.0
            image = PIL.Image.open(target)
            width, height = image.size
            with open(target, "rb") as fi:
                base64 = get_image_base64(UploadedFile(fi, name=filename))
                findings = list(processor.find_text(target, text, mode=mode, debug=True))
                if findings and not findings[0].match:
                    errors.append(findings)
                    si = findings[0]
                elif findings and findings[0].match and findings[0].match.distance == 0:
                    success.append(findings)
                    si = findings[0]
                elif findings and findings[0].match and findings[0].match.distance > 0:
                    warnings.append(findings)
                    si = findings[0]
                else:
                    errors.append(findings)
                    si = processor.debug_info.iterations[-1]
                lines.append(
                    {
                        "filename": filename,
                        "filesize": naturalsize(size, False, True, "%.3f"),
                        "search_text": text,
                        "image": base64,
                        "info": f"{int(width)}x{int(height)}",
                        "si": si,
                        "class": get_class(si) if si else "",
                    }
                )
    report = Path(__file__).parent.parent.parent / f".report_{mode.name}.html"
    template = Template((Path(__file__).parent / "template.html").read_text(encoding="utf-8"))
    with Path(report).open("w", encoding="utf-8") as f:
        f.write(
            template.render(
                Context(
                    {
                        "lines": lines,
                        "timing": m,
                        "mode": mode,
                        "errors": errors,
                        "warnings": warnings,
                        "success": success,
                    }
                )
            )
        )
