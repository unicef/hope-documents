import csv
import logging
import os
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import click
from PIL.ExifTags import TAGS
from colorama import Fore, Style
from humanize import naturalsize
from jinja2 import Template

from hope_documents.exceptions import InvalidImageError
from hope_documents.ocr.engine import CV2Config, MatchMode, Processor, ScanEntryInfo, Scanner, SearchInfo, TSConfig
from hope_documents.utils.image import get_image, get_image_base64
from hope_documents.utils.language import parse_bool
from hope_documents.utils.logging import LevelFormatter
from hope_documents.utils.timeit import time_it

logger = logging.getLogger(__name__)
INFO_LINE = f"{Fore.YELLOW}%-16s: {Style.RESET_ALL}%s"


def configure_logging(debug: bool, loggers: Iterable[str] = ("hope_documents",)) -> None:
    # This should be called only from a click command
    formatter = LevelFormatter()
    ch = logging.StreamHandler()
    ch.setFormatter(formatter)
    for log_name in loggers:
        logr = logging.getLogger(log_name)
        logr.handlers = []
        if debug:
            logr.setLevel(logging.DEBUG)
            logr.addHandler(ch)


def write_report(output_filename: str, template_name: str, context: dict[str, Any]) -> None:
    report = Path(".") / output_filename
    click.echo(f"Writing report to {report}")
    template = Template((Path(__file__).parent / template_name).read_text(encoding="utf-8"))
    with Path(report).open("w", encoding="utf-8") as f:
        f.write(template.render(context))


def load_expectations(filename: str) -> dict[str, tuple[str, bool, float]]:
    expected_values = {}

    with Path(filename).open("r", encoding="utf-8", newline="") as f:
        reader = csv.reader(f, delimiter=",", quotechar='"', quoting=csv.QUOTE_ALL, skipinitialspace=True)
        for row in reader:
            expected_values[row[0]] = str(row[1]), parse_bool(row[2]), float(row[3])
    return expected_values


@click.group(name="doc")
def cli() -> None:
    pass


@cli.command()
@click.argument("filepaths", nargs=-1, type=click.Path(exists=True), required=True)
@click.option("-a", "--auto", default=False, is_flag=True)
@click.option("-t", "--threshold", default=128, help="cv2 threshold [0..255]")
@click.option("-p", "--psm", default=11, help="TS Page segmentation mode [0..13]")
@click.option("-o", "--oem", default=3, help="TS OCR Engine mode [0..3]")
@click.option("-n", "--number-only", default=False, is_flag=True, help="Only extract numbers")
@click.option("-r", "--rotate", default=0, help="Rotate image")
@click.option("-s", "--pattern", default="", help="Pattern to search")
@click.option("--debug", is_flag=True, help="Debug mode")
def extract(filepaths: list[click.Path], debug: bool, **kwargs: Any) -> None:
    configure_logging(debug)
    ret_code = 0

    def cb(info: ScanEntryInfo) -> None:
        click.echo(f"{Fore.YELLOW}Loader: {Fore.LIGHTWHITE_EX}{info.loader}{Fore.RESET}")
        if err := info.error:
            click.echo(f"{Fore.RED}{err}{Fore.RESET}")
        click.echo(f"{Fore.GREEN}{info.text}{Fore.RESET}")
        click.echo(f"{Fore.LIGHTWHITE_EX}========{Fore.RESET}")

    def cb1(info: SearchInfo) -> None:
        click.echo(f"{Fore.YELLOW}Loader: {Fore.LIGHTWHITE_EX}{info.loader}{Fore.RESET}")
        if err := info.error:
            click.echo(f"{Fore.RED}{err}{Fore.RESET}")
        click.echo(f"Match: {Fore.GREEN}{info.match.text if info.match else 'N/A'}{Fore.RESET}")
        click.echo(f"Distance: {Fore.GREEN}{info.match.distance if info.match else 'N/A'}{Fore.RESET}")
        click.echo(f"{Fore.LIGHTWHITE_EX}========{Fore.RESET}")

    ts_config = TSConfig(oem=kwargs["oem"], psm=kwargs["psm"], number_only=kwargs["number_only"])
    p = Processor(ts_config=ts_config, cv2_config=CV2Config(threshold=kwargs["threshold"]))
    click.echo(f"{Fore.YELLOW}Config: {Fore.LIGHTWHITE_EX}{ts_config}{Fore.RESET}")
    scanner = Scanner(*filepaths)
    for file in scanner.files:
        click.echo(f"{Fore.YELLOW}File: {Fore.LIGHTWHITE_EX}{file}{Fore.RESET}")
        if kwargs["pattern"]:
            image = get_image(file)
            for findings in p.find_text(image, kwargs["pattern"], rotations=[kwargs["rotate"]]):
                cb1(findings)
        else:
            for extracted in p.process(file, rotate=kwargs["rotate"]):
                cb(extracted)
                if extracted.error != "":
                    ret_code = 1
    click.get_current_context().exit(ret_code)


@cli.command()
@click.argument("filepaths", nargs=-1, type=click.Path(exists=True), required=True)
@click.option("-e", "--expectations", type=click.File("r"), required=True)
@click.option("-m", "--mode", "mode", default=MatchMode.FIRST.name, type=click.Choice(MatchMode), help="Match mode")
@click.option("--debug", is_flag=True, help="Debug mode")
def report(filepaths: list[click.Path], mode: MatchMode, expectations: click.File, debug: bool, **kwargs: Any) -> None:
    lines = []
    errors = []
    warnings = []
    success = []
    expected_values = load_expectations(expectations.name)
    scanner = Scanner(*filepaths)
    processor = Processor(ts_config=TSConfig(), cv2_config=CV2Config())
    with time_it() as m:
        for filename in scanner.files:
            target = Path(filename)
            file_label = str(target.absolute().relative_to(os.getcwd()))

            if entry := expected_values.get(file_label):
                text, found, distance = entry
                size = target.stat().st_size / 1024.0
                try:
                    image = get_image(str(target))
                    width, height = image.size
                    info = f"{int(width)}x{int(height)}"
                    base64 = get_image_base64(image)
                except InvalidImageError:
                    si = info = None
                    base64 = ""
                else:
                    findings = list(processor.find_text(image, text, mode=mode, debug=True))
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
                        "info": info,
                        "si": si,
                    }
                )
        write_report(
            f".report_{mode.name}.html",
            "report.html",
            {
                "lines": lines,
                "timing": m,
                "mode": mode,
                "errors": errors,
                "warnings": warnings,
                "success": success,
            },
        )


@cli.command()
@click.argument("filepath", type=click.File(), required=True)
@click.option("-e", "--expectations", type=click.File("r"), required=True)
@click.option("-m", "--mode", "mode", default=MatchMode.FIRST.name, type=click.Choice(MatchMode), help="Match mode")
@click.option("--debug", is_flag=True, help="Debug mode")
def inspect(filepath: click.File, mode: MatchMode, expectations: click.File, debug: bool, **kwargs: Any) -> None:
    expected_values = load_expectations(expectations.name)

    target = Path(filepath.name)
    file_label = str(target.absolute().relative_to(os.getcwd()))
    data = []

    if expected_args := expected_values.get(file_label):
        pattern, found, distance = expected_args
    else:
        pattern = None
    try:
        original = get_image(str(target))
    except InvalidImageError as e:
        click.get_current_context().fail(str(e))

    with time_it() as m:
        processor = Processor(ts_config=TSConfig(), cv2_config=CV2Config())
        image_info: dict[str, Any] = {}
        image_info["size"] = naturalsize(target.stat().st_size, False, True, "%.3f")
        image_info["dim"] = original.size
        exifdata = original.getexif()
        for tag_id in exifdata:
            tag = str(TAGS.get(tag_id, tag_id))
            value = exifdata.get(tag_id)
            if isinstance(value, bytes):
                value = value.decode(errors="ignore")
            image_info[tag] = str(value)

        for loader in processor.loaders:
            for image, angle in loader.rotate(original):
                if expected_args and pattern:
                    text, match = processor.find_single(image, pattern)
                else:
                    text = ""
                    match = None
                data.append(
                    {
                        "loader": loader.__class__.__name__,
                        "angle": angle,
                        "match": match,
                        "pattern": pattern,
                        "image": get_image_base64(image),
                        "text": text,
                    }
                )
        write_report(
            f".inspect_{mode.name}.html",
            "inspect.html",
            {
                "filename": file_label,
                "data": data,
                "timing": m,
                "mode": mode,
                "original": get_image_base64(original),
                "image_info": image_info,
            },
        )
