import os
from unittest import mock
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from hope_ocr.ocr.__cli__ import cli


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


def test_inspect_help(runner: CliRunner) -> None:
    result = runner.invoke(cli, ["report", "--help"])
    assert not result.stderr
    assert result.exit_code == 0


@patch("hope_ocr.ocr.__cli__.write_report")
def test_inspect(write_report_mock, runner: CliRunner, test_dir, images_dir) -> None:
    images_file = images_dir / "and" / "pp1.png"
    expectations_file = test_dir / "ocr" / "expectations.csv"
    with mock.patch.object(os, "getcwd", return_value=str(test_dir.parent.absolute())):
        result = runner.invoke(
            cli,
            [
                "inspect",
                "--expectations",
                str(expectations_file),
                str(images_file),
            ],
            catch_exceptions=False,
        )
        assert result.exit_code == 0, result.output
        assert "unexistent.png" not in result.output
        write_report_mock.assert_called_once()
        args, kwargs = write_report_mock.call_args
        assert args[0] == ".inspect_FIRST.html"
        assert args[1] == "inspect.html"
