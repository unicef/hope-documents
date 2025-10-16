import os
from pathlib import Path
from unittest import mock
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from hope_documents.ocr.__cli__ import cli

images_dirs = [
    #    str((Path(__file__).parent.parent / "images/and").absolute()),
    #    str((Path(__file__).parent.parent / "images/sdn").absolute()),
    str((Path(__file__).parent.parent / "images/ita").absolute()),
    str((Path(__file__).parent.parent / "images/_invalid").absolute()),
]
expectations_file = Path(__file__).parent.parent / "ocr" / "expectations.csv"


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


def test_report_help(runner: CliRunner) -> None:
    result = runner.invoke(cli, ["report", "--help"])
    assert not result.stderr
    assert result.exit_code == 0


@patch("hope_documents.ocr.__cli__.write_report")
def test_report(write_report_mock, runner: CliRunner, test_dir) -> None:
    with mock.patch.object(os, "getcwd", return_value=str(test_dir.parent.absolute())):
        result = runner.invoke(
            cli,
            [
                "report",
                "--expectations",
                str(expectations_file),
                *images_dirs,
            ],
            catch_exceptions=False,
        )
        assert result.exit_code == 0, result.output
        assert "unexistent.png" not in result.output
        write_report_mock.assert_called_once()
        args, kwargs = write_report_mock.call_args
        assert args[0] == ".report_FIRST.html"
        assert args[1] == "report.html"
