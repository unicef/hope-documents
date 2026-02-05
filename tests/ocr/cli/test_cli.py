import csv
import logging
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from hope_ocr.ocr.__cli__ import cli, configure_logging, load_expectations, write_report


def test_load_expectations(tmp_path):
    """Test that expectations are loaded correctly from a CSV file."""
    csv_file = tmp_path / "expectations.csv"
    with csv_file.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["file1.png", "expected_text", "True", "0.9"])
        writer.writerow(["file2.png", "another_text", "False", "0.8"])

    expected = {
        "file1.png": ("expected_text", True, 0.9),
        "file2.png": ("another_text", False, 0.8),
    }
    assert load_expectations(str(csv_file)) == expected


@patch("hope_ocr.ocr.__cli__.Template")
@patch("hope_ocr.ocr.__cli__.click.echo")
def test_write_report(mock_echo, mock_template, tmp_path):
    """Test that the report is written correctly."""
    output_file = tmp_path / "report.html"
    template_content = "Hello {{ content }}"
    mock_template.return_value.render.return_value = "Hello World"
    # we need to mock the reading of the template file
    with patch("hope_ocr.ocr.__cli__.Path.read_text", return_value=template_content):
        write_report(str(output_file), "dummy_template.html", {"content": "World"})

    mock_echo.assert_called_with(f"Writing report to {output_file}")
    mock_template.assert_called_with(template_content)
    assert output_file.read_text() == "Hello World"


def test_configure_logging_debug():
    """Test that logging is configured correctly for debug mode."""
    logger_name = "hope_ocr"
    configure_logging(debug=True, loggers=[logger_name])
    assert logging.getLogger(logger_name).level == logging.DEBUG


def test_configure_logging_no_debug():
    """Test that logging is configured correctly for non-debug mode."""
    logger_name = "hope_ocr"
    logger = logging.getLogger(logger_name)
    initial_level = logger.level
    configure_logging(debug=False, loggers=[logger_name])
    assert logger.level == initial_level  # No change if not debug
    assert not logger.handlers


@patch("hope_ocr.ocr.__cli__.Scanner")
@patch("hope_ocr.ocr.__cli__.Processor")
def test_extract_command(mock_processor, mock_scanner, tmp_path):
    """Test the extract command."""
    runner = CliRunner()
    image_file = tmp_path / "image.png"
    image_file.touch()

    mock_scanner.return_value.files = [str(image_file)]
    mock_processor.return_value.process.return_value = [MagicMock(text="extracted text", error="")]

    result = runner.invoke(cli, ["extract", str(image_file)])
    assert result.exit_code == 0
    assert "extracted text" in result.output


@patch("hope_ocr.ocr.__cli__.os.getcwd")
@patch("hope_ocr.ocr.__cli__.get_image")
@patch("hope_ocr.ocr.__cli__.Scanner")
@patch("hope_ocr.ocr.__cli__.Processor")
@patch("hope_ocr.ocr.__cli__.write_report")
@patch("hope_ocr.ocr.__cli__.get_image_base64")
def test_report_command(
    mock_get_image_base64,
    mock_write_report,
    mock_processor,
    mock_scanner,
    mock_get_image,
    mock_getcwd,
    tmp_path,
):
    """Test the report command."""
    mock_get_image_base64.return_value = "base64string"
    mock_getcwd.return_value = str(tmp_path)
    runner = CliRunner()
    image_file = tmp_path / "image.png"
    image_file.touch()
    expectations_file = tmp_path / "expectations.csv"
    with expectations_file.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([str(image_file.relative_to(tmp_path)), "text", "True", "0.0"])

    mock_scanner.return_value.files = [str(image_file)]
    mock_match = MagicMock()
    mock_match.distance = 0
    mock_findings = MagicMock()
    mock_findings.match = mock_match
    mock_processor.return_value.find_text.return_value = [mock_findings]
    image_mock = MagicMock()
    image_mock.size = (100, 100)
    mock_get_image.return_value = image_mock

    result = runner.invoke(cli, ["report", str(image_file), "--expectations", str(expectations_file)])
    assert result.exit_code == 0
    assert mock_write_report.called


@patch("hope_ocr.ocr.__cli__.os.getcwd")
@patch("hope_ocr.ocr.__cli__.get_image")
@patch("hope_ocr.ocr.__cli__.Processor")
@patch("hope_ocr.ocr.__cli__.write_report")
@patch("hope_ocr.ocr.__cli__.get_image_base64")
def test_inspect_command(
    mock_get_image_base64,
    mock_write_report,
    mock_processor,
    mock_get_image,
    mock_getcwd,
    tmp_path,
):
    """Test the inspect command."""
    mock_get_image_base64.return_value = "base64string"
    mock_getcwd.return_value = str(tmp_path)
    runner = CliRunner()
    image_file = tmp_path / "image.png"
    image_file.touch()
    expectations_file = tmp_path / "expectations.csv"
    with expectations_file.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([str(image_file.relative_to(tmp_path)), "text", "True", "0.0"])

    mock_get_image.return_value = MagicMock()
    mock_get_image.return_value.getexif.return_value = {}

    result = runner.invoke(cli, ["inspect", str(image_file), "--expectations", str(expectations_file)])
    assert result.exit_code == 0
    assert mock_write_report.called
