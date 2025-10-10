import logging
from collections.abc import Iterable
from typing import Any

import click
from colorama import Fore, Style

from hope_documents.ocr.engine import CV2Config, Processor, ScanInfo, Scanner, TSConfig
from hope_documents.utils.logging import LevelFormatter

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


@click.command()
@click.argument("filepaths", nargs=-1, type=click.Path(exists=True), required=True)
@click.option("-a", "--auto", default=False, is_flag=True)
@click.option("-t", "--threshold", default=128, help="cv2 threshold [0..255]")
@click.option("-p", "--psm", default=11, help="TS Page segmentation mode [0..13]")
@click.option("-o", "--oem", default=3, help="TS OCR Engine mode [0..3]")
@click.option("-n", "--number-only", default=False, is_flag=True, help="Only extract numbers")
@click.option("--debug", is_flag=True, help="Debug mode")
def cli(filepaths: list[click.Path], debug: bool, **kwargs: Any) -> None:
    configure_logging(debug)
    ret_code = 0

    def cb(info: ScanInfo) -> None:
        click.echo(f"{Fore.YELLOW}Loader: {Fore.LIGHTWHITE_EX}{info.loader}{Fore.RESET}")
        if err := info.error:
            click.echo(f"{Fore.RED}{err}{Fore.RESET}")
        click.echo(f"{Fore.GREEN}{info.text}{Fore.RESET}")
        click.echo(f"{Fore.LIGHTWHITE_EX}========{Fore.RESET}")

    ts_config = TSConfig(oem=kwargs["oem"], psm=kwargs["psm"], number_only=kwargs["number_only"])
    p = Processor(ts_config=ts_config, cv2_config=CV2Config(threshold=kwargs["threshold"]))
    click.echo(f"{Fore.YELLOW}Config: {Fore.LIGHTWHITE_EX}{ts_config}{Fore.RESET}")
    scanner = Scanner(*filepaths)
    for file in scanner.files:
        click.echo(f"{Fore.YELLOW}File: {Fore.LIGHTWHITE_EX}{file}{Fore.RESET}")
        for extracted in p.process(file):
            cb(extracted)
            if extracted.error != "":
                ret_code = 1
    click.get_current_context().exit(ret_code)
