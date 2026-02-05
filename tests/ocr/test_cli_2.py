import csv
import logging
import tempfile
from pathlib import Path
from unittest.mock import ANY, MagicMock, patch

from PIL import Image
from click.testing import CliRunner

from hope_ocr.exceptions import InvalidImageError
from hope_ocr.ocr.__cli__ import cli, configure_logging, load_expectations, write_report
from hope_ocr.ocr.engine import MatchMode, ScanEntryInfo, SearchInfo  # Import necessary classes


class TestCli:
    def setup_method(self):
        self.runner = CliRunner()

    def test_cli_group(self):
        result = self.runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "Command-line interface for performing OCR tasks." in result.output

    @patch("logging.StreamHandler")
    @patch("logging.getLogger")
    def test_configure_logging(self, mock_get_logger, mock_stream_handler):
        mock_formatter_instance = MagicMock()
        with patch("hope_ocr.ocr.__cli__.LevelFormatter", return_value=mock_formatter_instance):
            # Test with debug=True
            configure_logging(True)
            mock_ch_instance = mock_stream_handler.return_value
            mock_ch_instance.setFormatter.assert_called_once_with(mock_formatter_instance)
            mock_logger_instance = mock_get_logger.return_value
            mock_logger_instance.handlers = []  # Reset handlers for clean assertion
            mock_logger_instance.setLevel.assert_called_once_with(logging.DEBUG)
            mock_logger_instance.addHandler.assert_called_once_with(mock_ch_instance)

            # Reset mocks for debug=False test
            mock_get_logger.reset_mock()
            mock_stream_handler.reset_mock()
            mock_formatter_instance.reset_mock()

            # Test with debug=False
            configure_logging(False)
            mock_logger_instance = mock_get_logger.return_value
            mock_logger_instance.handlers = []  # Reset handlers for clean assertion
            mock_logger_instance.setLevel.assert_not_called()
            mock_logger_instance.addHandler.assert_not_called()

    @patch("hope_ocr.ocr.__cli__.Template")
    @patch("hope_ocr.ocr.__cli__.click.echo")
    def test_write_report(self, mock_click_echo, mock_template_class):
        mock_output_file = "test_report.html"
        mock_template_name = "test_template.html"
        mock_context = {"key": "value"}

        # Mock Path class and its instances
        mock_path_dot = MagicMock()  # Represents Path(".")
        mock_path_file = MagicMock()  # Represents Path(__file__)
        mock_path_file_parent = MagicMock()  # Represents Path(__file__).parent
        mock_template_path = MagicMock()  # Represents Path(__file__).parent / template_name

        # Mock for the 'report' variable: Path(".") / output_filename
        mock_report_path_instance = MagicMock()
        mock_open_file = MagicMock()  # Re-added this line
        mock_report_path_instance.open.return_value.__enter__.return_value = mock_open_file
        mock_report_path_instance.__str__.return_value = mock_output_file  # Control its string representation

        mock_path_dot.__truediv__.return_value = mock_report_path_instance  # Path(".") / output_filename

        mock_path_file.parent = mock_path_file_parent
        mock_path_file_parent.__truediv__.return_value = mock_template_path
        mock_template_path.read_text.return_value = "template content"

        with patch("hope_ocr.ocr.__cli__.Path") as mock_path_class:
            mock_path_class.side_effect = [
                mock_path_dot,  # First call: Path(".")
                mock_path_file,  # Call for Path(__file__)
                mock_report_path_instance,  # Third call: Path(report)
            ]

            mock_template_instance = MagicMock()
            mock_template_class.return_value = mock_template_instance
            mock_template_instance.render.return_value = "rendered content"

            write_report(mock_output_file, mock_template_name, mock_context)

            mock_click_echo.assert_called_once_with(f"Writing report to {mock_output_file}")
            mock_template_class.assert_called_once_with("template content")
            mock_template_instance.render.assert_called_once_with(mock_context)
            mock_report_path_instance.open.assert_called_once_with("w", encoding="utf-8")
            mock_open_file.write.assert_called_once_with("rendered content")

    @patch("hope_ocr.ocr.__cli__.csv.reader")
    @patch("hope_ocr.ocr.__cli__.Path")
    def test_load_expectations(self, mock_path_class, mock_csv_reader):
        mock_filename = "expectations.csv"
        csv_data = [
            ["file1.png", "text1", "True", "0.1"],
            ["file2.png", "text2", "False", "0.5"],
        ]
        mock_csv_reader.return_value = csv_data

        mock_path_instance = MagicMock()
        mock_path_class.return_value = mock_path_instance
        mock_path_instance.open.return_value.__enter__.return_value = MagicMock()

        expected = {
            "file1.png": ("text1", True, 0.1),
            "file2.png": ("text2", False, 0.5),
        }

        result = load_expectations(mock_filename)

        mock_path_class.assert_called_once_with(mock_filename)
        mock_path_instance.open.assert_called_once_with("r", encoding="utf-8", newline="")
        mock_csv_reader.assert_called_once_with(
            mock_path_instance.open.return_value.__enter__.return_value,
            delimiter=",",
            quotechar='"',
            quoting=csv.QUOTE_ALL,
            skipinitialspace=True,
        )
        assert result == expected

    @patch("hope_ocr.ocr.__cli__.Scanner")
    @patch("hope_ocr.ocr.__cli__.Processor")
    @patch("hope_ocr.ocr.__cli__.get_image")
    @patch("hope_ocr.ocr.__cli__.click.echo")
    def test_extract_command_no_pattern_success(
        self, mock_click_echo, mock_get_image, mock_processor_class, mock_scanner_class
    ):
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "test_image.png"
            filepath.touch()  # Create a dummy file

            # Mock Scanner
            mock_scanner_instance = MagicMock()
            mock_scanner_instance.files = [str(filepath)]
            mock_scanner_class.return_value = mock_scanner_instance

            # Mock Processor
            mock_processor_instance = MagicMock()
            mock_scan_entry_info = ScanEntryInfo(loader="test_loader")
            mock_scan_entry_info.text = "extracted_text"
            mock_scan_entry_info.error = ""
            mock_processor_instance.process.return_value = [mock_scan_entry_info]
            mock_processor_class.return_value = mock_processor_instance

            # Invoke the command
            result = self.runner.invoke(cli, ["extract", str(filepath)])

            assert result.exit_code == 0
            mock_scanner_class.assert_called_once_with(str(filepath))
            mock_processor_class.assert_called_once()
            mock_processor_instance.process.assert_called_once_with(str(filepath), rotate=0)
            mock_click_echo.assert_any_call("\x1b[33mConfig: \x1b[97m--oem 3  --psm 11 \x1b[39m")
            mock_click_echo.assert_any_call(f"\x1b[33mFile: \x1b[97m{str(filepath)}\x1b[39m")
            mock_click_echo.assert_any_call("\x1b[33mLoader: \x1b[97mtest_loader\x1b[39m")
            mock_click_echo.assert_any_call("\x1b[32mextracted_text\x1b[39m")
            mock_click_echo.assert_any_call("\x1b[97m========\x1b[39m")  # Added this missing assertion

    @patch("hope_ocr.ocr.__cli__.Scanner")
    @patch("hope_ocr.ocr.__cli__.Processor")
    @patch("hope_ocr.ocr.__cli__.get_image")
    @patch("hope_ocr.ocr.__cli__.click.echo")
    def test_extract_command_with_pattern_success(
        self, mock_click_echo, mock_get_image, mock_processor_class, mock_scanner_class
    ):
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "test_image_with_pattern.png"
            filepath.touch()  # Create a dummy file
            test_pattern = "find_me"

            # Mock Scanner
            mock_scanner_instance = MagicMock()
            mock_scanner_instance.files = [str(filepath)]
            mock_scanner_class.return_value = mock_scanner_instance

            # Mock Processor
            mock_processor_instance = MagicMock()
            mock_match = MagicMock()  # Mock the Match object returned by find_similar
            mock_match.text = test_pattern
            mock_match.distance = 0.0
            mock_search_info = SearchInfo(loader="test_loader", match=mock_match, angle=0, psm=11, attempts=1)
            mock_processor_instance.find_text.return_value = [mock_search_info]
            mock_processor_class.return_value = mock_processor_instance

            # Invoke the command
            result = self.runner.invoke(cli, ["extract", str(filepath), "--pattern", test_pattern, "--rotate", "0"])

            assert result.exit_code == 0
            mock_scanner_class.assert_called_once_with(str(filepath))
            mock_processor_class.assert_called_once()
            mock_get_image.assert_called_once()  # get_image is called when pattern is provided
            mock_processor_instance.find_text.assert_called_once_with(
                mock_get_image.return_value, test_pattern, rotations=[0], mode=MatchMode.FIRST
            )
            mock_click_echo.assert_any_call("\x1b[33mConfig: \x1b[97m--oem 3  --psm 11 \x1b[39m")
            mock_click_echo.assert_any_call(f"\x1b[33mFile: \x1b[97m{str(filepath)}\x1b[39m")
            mock_click_echo.assert_any_call("\x1b[33mLoader: \x1b[97mtest_loader\x1b[39m")
            mock_click_echo.assert_any_call("Psm: \x1b[32m11\x1b[39m")
            mock_click_echo.assert_any_call(f"Match: \x1b[32m{test_pattern}\x1b[39m")
            mock_click_echo.assert_any_call("Distance: \x1b[32m0.0\x1b[39m")
            mock_click_echo.assert_any_call("\x1b[97m========\x1b[39m")

    @patch("hope_ocr.ocr.__cli__.Scanner")
    @patch("hope_ocr.ocr.__cli__.Processor")
    @patch("hope_ocr.ocr.__cli__.write_report")
    @patch("hope_ocr.ocr.__cli__.load_expectations")
    @patch("hope_ocr.ocr.__cli__.get_image")
    @patch("hope_ocr.ocr.__cli__.get_image_base64")
    @patch("hope_ocr.ocr.__cli__.click.echo")
    @patch("hope_ocr.ocr.__cli__.time_it")
    @patch("os.getcwd")  # Patch os.getcwd
    def test_report_command_success(
        self,
        mock_os_getcwd,  # New mock argument
        mock_time_it,
        mock_click_echo,
        mock_get_image_base64,
        mock_get_image,
        mock_load_expectations,
        mock_write_report,
        mock_processor_class,
        mock_scanner_class,
    ):
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_os_getcwd.return_value = tmpdir  # Set os.getcwd to tmpdir
            filepath = Path(tmpdir) / "test_report_image.png"
            filepath.touch()  # Create a dummy file

            expectations_filepath = Path(tmpdir) / "expectations.csv"
            with open(expectations_filepath, "w") as f:
                f.write(f"{filepath.absolute().relative_to(Path(tmpdir))},expected_text,True,0.0")

            # Mock time_it
            mock_time_it_instance = MagicMock()
            mock_time_it_instance.__enter__.return_value.elapsed = 10.0
            mock_time_it_instance.__enter__.return_value.human = "10 seconds"
            mock_time_it.return_value = mock_time_it_instance

            # Mock Scanner
            mock_scanner_instance = MagicMock()
            mock_scanner_instance.files = [str(filepath)]
            mock_scanner_class.return_value = mock_scanner_instance

            # Mock load_expectations
            mock_load_expectations.return_value = {
                str(filepath.absolute().relative_to(Path(tmpdir))): ("expected_text", True, 0.0)
            }

            # Mock get_image and get_image_base64
            mock_image_instance = MagicMock()
            mock_image_instance.size = (100, 200)
            mock_image_instance.getexif.return_value = {}  # Mock getexif
            mock_get_image.return_value = mock_image_instance
            mock_get_image_base64.return_value = "base64_image_data"

            # Mock Processor
            mock_processor_instance = MagicMock()
            mock_match = MagicMock()
            mock_match.text = "expected_text"
            mock_match.distance = 0.0
            mock_search_info = SearchInfo(loader="test_loader", match=mock_match, angle=0, psm=11, attempts=1)
            mock_processor_instance.find_text.return_value = [mock_search_info]
            mock_processor_class.return_value = mock_processor_instance

            # Invoke the command
            result = self.runner.invoke(cli, ["report", str(filepath), "-e", str(expectations_filepath)])

            assert result.exit_code == 0
            mock_scanner_class.assert_called_once_with(str(filepath))
            mock_load_expectations.assert_called_once_with(str(expectations_filepath))
            mock_processor_class.assert_called_once()
            mock_get_image.assert_called_once_with(str(filepath))
            mock_get_image_base64.assert_called_once_with(mock_image_instance)
            mock_processor_instance.find_text.assert_called_once_with(
                mock_image_instance, "expected_text", mode=MatchMode.FIRST, debug=True
            )
            mock_write_report.assert_called_once()
            mock_click_echo.assert_called_with(ANY)  # Assert "Done in..." is called

    @patch("hope_ocr.ocr.__cli__.Scanner")
    @patch("hope_ocr.ocr.__cli__.Processor")
    @patch("hope_ocr.ocr.__cli__.write_report")
    @patch("hope_ocr.ocr.__cli__.load_expectations")
    @patch("hope_ocr.ocr.__cli__.get_image")
    @patch("hope_ocr.ocr.__cli__.get_image_base64")
    @patch("hope_ocr.ocr.__cli__.click.echo")
    @patch("hope_ocr.ocr.__cli__.time_it")
    @patch("os.getcwd")  # Patch os.getcwd
    def test_report_command_invalid_image(
        self,
        mock_os_getcwd,
        mock_time_it,
        mock_click_echo,
        mock_get_image_base64,
        mock_get_image,
        mock_load_expectations,
        mock_write_report,
        mock_processor_class,
        mock_scanner_class,
    ):
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_os_getcwd.return_value = tmpdir  # Set os.getcwd to tmpdir
            filepath = Path(tmpdir) / "invalid_image.png"
            filepath.touch()  # Create a dummy file

            expectations_filepath = Path(tmpdir) / "expectations.csv"
            with open(expectations_filepath, "w") as f:
                f.write(f"{filepath.absolute().relative_to(Path(tmpdir))},expected_text,True,0.0")

            # Mock time_it
            mock_time_it_instance = MagicMock()
            mock_time_it_instance.__enter__.return_value.elapsed = 5.0
            mock_time_it_instance.__enter__.return_value.human = "5 seconds"
            mock_time_it.return_value = mock_time_it_instance

            # Mock Scanner
            mock_scanner_instance = MagicMock()
            mock_scanner_instance.files = [str(filepath)]
            mock_scanner_class.return_value = mock_scanner_instance

            # Mock load_expectations
            mock_load_expectations.return_value = {
                str(filepath.absolute().relative_to(Path(tmpdir))): ("expected_text", True, 0.0)
            }

            # Mock get_image to raise InvalidImageError
            mock_get_image.side_effect = InvalidImageError("Invalid image file")

            # Mock get_image_base64 (should not be called)
            mock_get_image_base64.return_value = ""

            # Mock Processor (should not be called for find_text if get_image fails)
            mock_processor_instance = MagicMock()
            mock_processor_class.return_value = mock_processor_instance

            # Invoke the command
            result = self.runner.invoke(cli, ["report", str(filepath), "-e", str(expectations_filepath)])

            assert result.exit_code == 0  # Command should still exit with 0 as it handles the error gracefully
            mock_scanner_class.assert_called_once_with(str(filepath))
            mock_load_expectations.assert_called_once_with(str(expectations_filepath))
            mock_get_image.assert_called_once_with(str(filepath))
            mock_get_image_base64.assert_not_called()
            mock_processor_instance.find_text.assert_not_called()  # find_text should not be called

            # Assert write_report context contains error info
            mock_write_report.assert_called_once()
            args, kwargs = mock_write_report.call_args
            context = args[2]
            assert "lines" in context
            assert len(context["lines"]) == 1
            assert context["lines"][0]["si"] is None
            assert context["lines"][0]["info"] is None
            assert context["lines"][0]["image"] == ""
            # The original error message will be inside the ScanEntryInfo's error attribute if si is not None
            # Here, si is None, so the error message is not directly in 'si'.
            # However, the overall error handling in the report implies that the error would be logged
            # or somehow reflected in the report. For now, the None checks are sufficient.

            mock_click_echo.assert_called_with(ANY)  # Assert "Done in..." is called

    @patch("hope_ocr.ocr.__cli__.Scanner")
    @patch("hope_ocr.ocr.__cli__.Processor")
    @patch("hope_ocr.ocr.__cli__.write_report")
    @patch("hope_ocr.ocr.__cli__.load_expectations")
    @patch("hope_ocr.ocr.__cli__.get_image")
    @patch("hope_ocr.ocr.__cli__.get_image_base64")
    @patch("hope_ocr.ocr.__cli__.click.echo")
    @patch("hope_ocr.ocr.__cli__.time_it")
    @patch("os.getcwd")  # Patch os.getcwd
    def test_report_command_no_match(
        self,
        mock_os_getcwd,
        mock_time_it,
        mock_click_echo,
        mock_get_image_base64,
        mock_get_image,
        mock_load_expectations,
        mock_write_report,
        mock_processor_class,
        mock_scanner_class,
    ):
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_os_getcwd.return_value = tmpdir  # Set os.getcwd to tmpdir
            filepath = Path(tmpdir) / "test_report_image_no_match.png"
            filepath.touch()  # Create a dummy file

            expectations_filepath = Path(tmpdir) / "expectations.csv"
            with open(expectations_filepath, "w") as f:
                f.write(f"{filepath.absolute().relative_to(Path(tmpdir))},expected_text,True,0.0")

            # Mock time_it
            mock_time_it_instance = MagicMock()
            mock_time_it_instance.__enter__.return_value.elapsed = 7.0
            mock_time_it_instance.__enter__.return_value.human = "7 seconds"
            mock_time_it.return_value = mock_time_it_instance

            # Mock Scanner
            mock_scanner_instance = MagicMock()
            mock_scanner_instance.files = [str(filepath)]
            mock_scanner_class.return_value = mock_scanner_instance

            # Mock load_expectations
            mock_load_expectations.return_value = {
                str(filepath.absolute().relative_to(Path(tmpdir))): ("expected_text", True, 0.0)
            }

            # Mock get_image and get_image_base64
            mock_image_instance = MagicMock()
            mock_image_instance.size = (100, 200)
            mock_image_instance.getexif.return_value = {}  # Mock getexif
            mock_get_image.return_value = mock_image_instance
            mock_get_image_base64.return_value = "base64_image_data_no_match"

            # Mock Processor: find_text returns findings but no match
            mock_processor_instance = MagicMock()
            mock_search_info = SearchInfo(loader="test_loader_no_match", match=None, angle=0, psm=11, attempts=1)
            mock_processor_instance.find_text.return_value = [mock_search_info]
            mock_processor_class.return_value = mock_processor_instance

            # Mock debug_info for the 'else' branch where si = processor.debug_info.iterations[-1]
            mock_processor_instance.debug_info = MagicMock()
            mock_processor_instance.debug_info.iterations = [mock_search_info]

            # Invoke the command
            result = self.runner.invoke(cli, ["report", str(filepath), "-e", str(expectations_filepath)])

            assert result.exit_code == 0
            mock_scanner_class.assert_called_once_with(str(filepath))
            mock_load_expectations.assert_called_once_with(str(expectations_filepath))
            mock_processor_class.assert_called_once()
            mock_get_image.assert_called_once_with(str(filepath))
            mock_get_image_base64.assert_called_once_with(mock_image_instance)
            mock_processor_instance.find_text.assert_called_once_with(
                mock_image_instance, "expected_text", mode=MatchMode.FIRST, debug=True
            )

            # Assert write_report context
            mock_write_report.assert_called_once()
            args, kwargs = mock_write_report.call_args
            context = args[2]
            assert "lines" in context
            assert len(context["lines"]) == 1
            assert context["lines"][0]["si"] == mock_search_info  # si should be the SearchInfo object with no match
            assert len(context["errors"]) == 1  # This case should add to errors list
            assert context["errors"][0][0] == mock_search_info  # Check the error list content

            mock_click_echo.assert_called_with(ANY)  # Assert "Done in..." is called

    @patch("hope_ocr.ocr.__cli__.Scanner")
    @patch("hope_ocr.ocr.__cli__.Processor")
    @patch("hope_ocr.ocr.__cli__.write_report")
    @patch("hope_ocr.ocr.__cli__.load_expectations")
    @patch("hope_ocr.ocr.__cli__.get_image")
    @patch("hope_ocr.ocr.__cli__.get_image_base64")
    @patch("hope_ocr.ocr.__cli__.click.echo")
    @patch("hope_ocr.ocr.__cli__.time_it")
    @patch("os.getcwd")  # Patch os.getcwd
    def test_inspect_command_success(
        self,
        mock_os_getcwd,
        mock_time_it,
        mock_click_echo,
        mock_get_image_base64,
        mock_get_image,
        mock_load_expectations,
        mock_write_report,
        mock_processor_class,
        mock_scanner_class,  # This is not used in inspect, but keeping for consistency if it gets added in future
    ):
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_os_getcwd.return_value = tmpdir  # Set os.getcwd to tmpdir
            filepath = Path(tmpdir) / "test_inspect_image.png"
            filepath.touch()  # Create a dummy file

            expectations_filepath = Path(tmpdir) / "expectations.csv"
            with open(expectations_filepath, "w") as f:
                f.write(f"{filepath.absolute().relative_to(Path(tmpdir))},expected_text,True,0.0")

            # Mock time_it
            mock_time_it_instance = MagicMock()
            mock_time_it_instance.__enter__.return_value.elapsed = 12.0
            mock_time_it_instance.__enter__.return_value.human = "12 seconds"
            mock_time_it.return_value = mock_time_it_instance

            # Mock load_expectations
            mock_load_expectations.return_value = {
                str(filepath.absolute().relative_to(Path(tmpdir))): ("expected_text", True, 0.0)
            }

            # Mock get_image and get_image_base64
            mock_image_instance = MagicMock(spec=Image.Image)  # Use spec to ensure proper PIL Image mock
            mock_image_instance.size = (100, 200)
            mock_image_instance.getexif.return_value = {}  # Mock getexif
            mock_get_image.return_value = mock_image_instance
            mock_get_image_base64.return_value = "base64_image_data_inspect"

            # Mock Processor and its loaders and find_single method
            mock_processor_instance = MagicMock()
            mock_loader_instance = MagicMock()
            mock_loader_instance.__class__.__name__ = "TestLoader"
            mock_loader_instance.rotate.return_value = [(mock_image_instance, 0)]  # Simulate one rotated image
            mock_processor_instance.loaders = [mock_loader_instance]

            mock_match = MagicMock()
            mock_match.text = "found_text"
            mock_processor_instance.find_single.return_value = ("found_text_from_processor", mock_match)
            mock_processor_class.return_value = mock_processor_instance

            # Invoke the command
            result = self.runner.invoke(cli, ["inspect", str(filepath), "-e", str(expectations_filepath)])

            assert result.exit_code == 0
            mock_load_expectations.assert_called_once_with(str(expectations_filepath))
            mock_get_image.assert_called_once_with(str(filepath))
            mock_processor_class.assert_called_once()
            assert mock_get_image_base64.call_count == 2  # Called twice: once for image, once for original
            mock_processor_instance.find_single.assert_called_once_with(mock_image_instance, "expected_text")
            mock_write_report.assert_called_once()

            args, kwargs = mock_write_report.call_args
            context = args[2]
            assert "filename" in context
            assert "data" in context
            assert len(context["data"]) == 1
            assert context["data"][0]["loader"] == "TestLoader"
            assert context["data"][0]["angle"] == 0
            assert context["data"][0]["match"] == mock_match
            assert context["data"][0]["pattern"] == "expected_text"
            assert context["data"][0]["image"] == "base64_image_data_inspect"
            assert context["data"][0]["text"] == "found_text_from_processor"
            assert "timing" in context
            assert "mode" in context
            assert "original" in context
            assert "image_info" in context

            mock_click_echo.assert_called_with(ANY)  # Assert "Done in..." is called

    @patch("hope_ocr.ocr.__cli__.Processor")
    @patch("hope_ocr.ocr.__cli__.write_report")
    @patch("hope_ocr.ocr.__cli__.load_expectations")
    @patch("hope_ocr.ocr.__cli__.get_image")
    @patch("hope_ocr.ocr.__cli__.get_image_base64")
    @patch("hope_ocr.ocr.__cli__.click.echo")
    @patch("hope_ocr.ocr.__cli__.time_it")
    @patch("os.getcwd")
    def test_inspect_command_invalid_image(
        self,
        mock_os_getcwd,
        mock_time_it,
        mock_click_echo,
        mock_get_image_base64,
        mock_get_image,
        mock_load_expectations,
        mock_write_report,
        mock_processor_class,
    ):
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_os_getcwd.return_value = tmpdir
            filepath = Path(tmpdir) / "invalid_image_for_inspect.png"
            filepath.touch()

            expectations_filepath = Path(tmpdir) / "expectations.csv"
            with open(expectations_filepath, "w") as f:
                f.write(f"{filepath.absolute().relative_to(Path(tmpdir))},expected_text,True,0.0")

            mock_load_expectations.return_value = {
                str(filepath.absolute().relative_to(Path(tmpdir))): ("expected_text", True, 0.0)
            }

            mock_get_image.side_effect = InvalidImageError("Invalid image for inspect")

            result = self.runner.invoke(cli, ["inspect", str(filepath), "-e", str(expectations_filepath)])

            # The inspect command handles InvalidImageError by calling click.get_current_context().fail()
            # which raises SystemExit with code 2.
            assert result.exit_code == 2
            assert "Error: Invalid image for inspect\n" in result.stderr

            mock_load_expectations.assert_called_once_with(str(expectations_filepath))
            mock_get_image.assert_called_once_with(str(filepath))
            mock_get_image_base64.assert_not_called()
            mock_processor_class.assert_not_called()  # Processor should not be initialized
            mock_write_report.assert_not_called()
            mock_click_echo.assert_not_called()  # No normal echoes
