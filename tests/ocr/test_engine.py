from unittest.mock import MagicMock, patch
from pathlib import Path
import tempfile
import os
import itertools

import pytest

from hope_ocr.ocr.engine import Scanner, CV2Config, TSConfig, Processor, MatchMode, ScanEntryInfo, SearchInfo, ScanInfo, SEARCH_TEST_PATTERN
from hope_ocr.exceptions import InvalidImageError, ExtractionError
from PIL import Image


class TestScanner:
    def test_init(self):
        scanner = Scanner("file1.png", "dir1")
        assert scanner.filepaths == ("file1.png", "dir1")

    def test_files_property_directory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            (tmp_path / "subdir1").mkdir()
            (tmp_path / "subdir1" / "file1.txt").touch()
            (tmp_path / "subdir2").mkdir()
            (tmp_path / "subdir2" / "file2.txt").touch()
            (tmp_path / "file3.txt").touch()

            scanner = Scanner(tmp_path)
            expected_files = [
                str(tmp_path / "file3.txt"),
                str(tmp_path / "subdir1" / "file1.txt"),
                str(tmp_path / "subdir2" / "file2.txt"),
            ]
            # Convert to Path objects for consistent comparison, then sort
            actual_files = sorted([str(Path(f)) for f in scanner.files])
            expected_files_sorted = sorted([str(Path(f)) for f in expected_files])
            assert actual_files == expected_files_sorted

    def test_files_property_single_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            file_path = tmp_path / "single_file.jpg"
            file_path.touch()

            scanner = Scanner(file_path)
            actual_files = list(scanner.files)
            assert actual_files == [str(file_path)]


class TestCV2Config:
    def test_init_default(self):
        config = CV2Config()
        assert config.threshold == 120

    def test_init_custom(self):
        config = CV2Config(threshold=150)
        assert config.threshold == 150

    def test_as_dict(self):
        config = CV2Config(threshold=100)
        assert config.as_dict() == {"threshold": 100}


class TestDataclasses:
    def test_scan_entry_info_repr(self):
        info = ScanEntryInfo(loader="TestLoader")
        assert repr(info) == "ScanEntryInfo(TestLoader)"
        assert info.text == ""
        assert info.error == ""
        assert info.time == ""

    def test_search_info_repr(self):
        mock_match = MagicMock() # Removed spec=MatchMode
        info = SearchInfo(loader="TestLoader", match=mock_match, angle=90, psm=6, attempts=3)
        info.time = "1s"
        assert repr(info) == "SearchInfo(TestLoader):<MagicMock id='{}'>:90:'1s'".format(id(mock_match))
        assert info.found is True

    def test_search_info_found_property(self):
        info = SearchInfo(loader="TestLoader", match=MagicMock())
        assert info.found is True
        info_no_match = SearchInfo(loader="TestLoader", match=None)
        assert info_no_match.found is False

    def test_scan_info_repr(self):
        info = ScanInfo()
        assert repr(info) == "ScanInfo([])"

class TestProcessor:
    @pytest.fixture
    def mock_ts_config(self):
        return MagicMock(spec=TSConfig)

    @pytest.fixture
    def mock_cv2_config(self):
        return MagicMock(spec=CV2Config)

    def test_init(self, mock_ts_config, mock_cv2_config):
        processor = Processor(mock_ts_config, mock_cv2_config)
        assert processor.ts_config == mock_ts_config
        assert processor.cv2_config == mock_cv2_config
        assert len(processor.loader_classes) > 0

        custom_loaders = [MagicMock(), MagicMock()]
        processor = Processor(mock_ts_config, mock_cv2_config, loaders=custom_loaders)
        assert processor.loader_classes == custom_loaders

    @patch("hope_ocr.ocr.engine.Loader")
    @patch("hope_ocr.ocr.engine.PILLoader")
    @patch("hope_ocr.ocr.engine.EnhancedLoader")
    @patch("hope_ocr.ocr.engine.CV2Loader")
    @patch("hope_ocr.ocr.engine.SmartLoader")
    @patch("hope_ocr.ocr.engine.BWLoader")
    @patch("hope_ocr.ocr.engine.ImprovedLoader")
    def test_loaders_property(
        self,
        MockImprovedLoader,
        MockBWLoader,
        MockSmartLoader,
        MockCV2Loader,
        MockEnhancedLoader,
        MockPILLoader,
        MockLoader,
        mock_ts_config,
        mock_cv2_config,
    ):
        mock_cv2_config.as_dict.return_value = {"threshold": 100}
        processor = Processor(mock_ts_config, mock_cv2_config)
        
        loaders = processor.loaders
        
        # Check that each loader class was instantiated with the cv2_config
        MockLoader.assert_called_once_with(threshold=100)
        MockPILLoader.assert_called_once_with(threshold=100)
        MockEnhancedLoader.assert_called_once_with(threshold=100)
        MockCV2Loader.assert_called_once_with(threshold=100)
        MockSmartLoader.assert_called_once_with(threshold=100)
        MockBWLoader.assert_called_once_with(threshold=100)
        MockImprovedLoader.assert_called_once_with(threshold=100)
        
        # Check that there are instances of these mocks in the loaders list
        assert MockLoader.return_value in loaders
        assert MockPILLoader.return_value in loaders
        assert MockEnhancedLoader.return_value in loaders
        assert MockCV2Loader.return_value in loaders
        assert MockSmartLoader.return_value in loaders
        assert MockBWLoader.return_value in loaders
        assert MockImprovedLoader.return_value in loaders
        
        # Check cached_property works (second access doesn't call __init__ again)
        _ = processor.loaders
        MockLoader.assert_called_once()


    @patch("hope_ocr.ocr.engine.Reader")
    def test_reader_property(self, MockReader, mock_ts_config, mock_cv2_config):
        processor = Processor(mock_ts_config, mock_cv2_config)
        reader = processor.reader
        MockReader.assert_called_once_with(mock_ts_config)
        assert reader == MockReader.return_value
        # Check cached_property works
        _ = processor.reader
        MockReader.assert_called_once()

    @patch("hope_ocr.ocr.engine.find_similar")
    def test_find_single_success(self, mock_find_similar, mock_ts_config, mock_cv2_config):
        mock_reader = MagicMock()
        mock_reader.extract.return_value = "extracted text"
        mock_ts_config.return_value = MagicMock() # Mock TSConfig initialization if needed
        processor = Processor(mock_ts_config, mock_cv2_config)
        processor.reader = mock_reader # Inject mock reader

        mock_image = MagicMock(spec=Image.Image)
        mock_match = MagicMock()
        mock_find_similar.return_value = mock_match

        text, match = processor.find_single(mock_image, "target text")

        mock_reader.extract.assert_called_once_with(mock_image)
        mock_find_similar.assert_called_once_with("target text", "extracted text", max_distance=5)
        assert text == "extracted text"
        assert match == mock_match

    @patch("hope_ocr.ocr.engine.find_similar", side_effect=ExtractionError("Test Error"))
    def test_find_single_extraction_error(self, mock_find_similar, mock_ts_config, mock_cv2_config):
        mock_reader = MagicMock()
        mock_reader.extract.return_value = "extracted text"
        mock_ts_config.return_value = MagicMock() # Mock TSConfig initialization if needed
        processor = Processor(mock_ts_config, mock_cv2_config)
        processor.reader = mock_reader # Inject mock reader

        mock_image = MagicMock(spec=Image.Image)

        text, match = processor.find_single(mock_image, "target text")

        mock_reader.extract.assert_called_once_with(mock_image)
        mock_find_similar.assert_called_once_with("target text", "extracted text", max_distance=5)
        assert text == "extracted text"
        assert match is None

    @patch("hope_ocr.ocr.engine.find_similar", side_effect=InvalidImageError("Invalid Image"))
    def test_find_single_invalid_image_error(self, mock_find_similar, mock_ts_config, mock_cv2_config):
        mock_reader = MagicMock()
        mock_reader.extract.return_value = "extracted text"
        mock_ts_config.return_value = MagicMock() # Mock TSConfig initialization if needed
        processor = Processor(mock_ts_config, mock_cv2_config)
        processor.reader = mock_reader # Inject mock reader

        mock_image = MagicMock(spec=Image.Image)

        text, match = processor.find_single(mock_image, "target text")

        mock_reader.extract.assert_called_once_with(mock_image)
        mock_find_similar.assert_called_once_with("target text", "extracted text", max_distance=5)
        assert text == "extracted text"
        assert match is None

    @patch("hope_ocr.ocr.engine.time_it")
    @patch("hope_ocr.ocr.engine.format_elapsed_time", return_value="1s")
    def test_processor_find_text_first_mode_success(
        self, mock_format_elapsed_time, mock_time_it, mock_ts_config, mock_cv2_config
    ):
        processor = Processor(mock_ts_config, mock_cv2_config)

        mock_loader = MagicMock()
        mock_loader.__class__.__name__ = "TestLoader"
        mock_loader.rotate.return_value = [(MagicMock(spec=Image.Image), 0)] # Simulate one rotated image
        processor.loaders = [mock_loader] # Inject mock loaders

        mock_reader = MagicMock()
        mock_reader.config = MagicMock()
        processor.reader = mock_reader # Inject mock reader

        mock_find_single_return = ("extracted text", MagicMock())
        processor.find_single = MagicMock(return_value=mock_find_single_return) # Mock find_single

        mock_time_it_instance = MagicMock()
        mock_time_it_instance.__enter__.return_value.get_partial.return_value = 1.0 # Elapsed time
        mock_time_it.return_value = mock_time_it_instance

        original_image = MagicMock(spec=Image.Image)
        target_text = "target"

        results = list(processor.find_text(original_image, target_text, mode=MatchMode.FIRST))

        assert len(results) == 1
        result = results[0]
        assert isinstance(result, SearchInfo)
        assert result.loader == "TestLoader"
        assert result.match == mock_find_single_return[1]
        assert result.text == mock_find_single_return[0]
        assert result.angle == 0
        assert result.psm == 11
        assert result.attempts == 1
        assert result.time == "1s"
        assert result.error == ""
        assert processor.reader.config.psm == 11 # Default psm
        processor.find_single.assert_called_once_with(mock_loader.rotate.return_value[0][0], target_text, max_errors=5)
        mock_loader.rotate.assert_called_once_with(original_image)
        mock_format_elapsed_time.assert_called_once_with(1.0)
        mock_time_it.assert_called_once()

    @patch("hope_ocr.ocr.engine.time_it")
    @patch("hope_ocr.ocr.engine.format_elapsed_time", return_value="1s")
    def test_processor_find_text_first_mode_find_single_error(
        self, mock_format_elapsed_time, mock_time_it, mock_ts_config, mock_cv2_config
    ):
        processor = Processor(mock_ts_config, mock_cv2_config)

        mock_loader = MagicMock()
        mock_loader.__class__.__name__ = "TestLoader"
        mock_loader.rotate.return_value = [(MagicMock(spec=Image.Image), 0)] # Simulate one rotated image
        processor.loaders = [mock_loader] # Inject mock loaders

        mock_reader = MagicMock()
        mock_reader.config = MagicMock()
        processor.reader = mock_reader # Inject mock reader

        processor.find_single = MagicMock(side_effect=InvalidImageError("Test Image Error")) # Mock find_single to raise error

        mock_time_it_instance = MagicMock()
        mock_time_it_instance.__enter__.return_value.get_partial.return_value = 1.0 # Elapsed time
        mock_time_it.return_value = mock_time_it_instance

        original_image = MagicMock(spec=Image.Image)
        target_text = "target"

        results = list(processor.find_text(original_image, target_text, mode=MatchMode.FIRST))

        assert len(results) == 0

    @patch("hope_ocr.ocr.engine.time_it")
    @patch("hope_ocr.ocr.engine.format_elapsed_time", return_value="2s")
    def test_processor_find_text_all_mode_success(
        self, mock_format_elapsed_time, mock_time_it, mock_ts_config, mock_cv2_config
    ):
        processor = Processor(mock_ts_config, mock_cv2_config)

        mock_loader1 = MagicMock()
        mock_loader1.__class__.__name__ = "Loader1"
        mock_loader1.rotate.return_value = [(MagicMock(spec=Image.Image), 0), (MagicMock(spec=Image.Image), 90)]
        mock_loader2 = MagicMock()
        mock_loader2.__class__.__name__ = "Loader2"
        mock_loader2.rotate.return_value = [(MagicMock(spec=Image.Image), 0)]
        processor.loaders = [mock_loader1, mock_loader2]

        mock_reader = MagicMock()
        mock_reader.config = MagicMock()
        processor.reader = mock_reader

        mock_match1 = MagicMock(distance=0.1) # Loader1, angle 0, psm 11
        mock_match2 = MagicMock(distance=0.2) # Loader1, angle 90, psm 11
        mock_match3 = MagicMock(distance=0.3) # Loader1, angle 0, psm 6
        mock_match4 = MagicMock(distance=0.4) # Loader1, angle 90, psm 6
        mock_match5 = MagicMock(distance=0.5) # Loader2, angle 0, psm 11
        mock_match6 = MagicMock(distance=0.6) # Loader2, angle 0, psm 6

        processor.find_single = MagicMock(side_effect=[
            ("text1", mock_match1),
            ("text2", mock_match2),
            ("text3", mock_match3),
            ("text4", mock_match4),
            ("text5", mock_match5),
            ("text6", mock_match6),
        ])

        mock_time_it_instance = MagicMock()
        mock_time_it_instance.__enter__.return_value.get_partial.side_effect = [i * 0.1 for i in range(1, 101)] # Sufficiently long list
        mock_time_it.return_value = mock_time_it_instance

        original_image = MagicMock(spec=Image.Image)
        target_text = "target"

        results = list(processor.find_text(original_image, target_text, mode=MatchMode.ALL))

        assert len(results) == 6

        # Result 0: Loader1, psm 11, angle 0
        assert results[0].loader == "Loader1"
        assert results[0].match == mock_match1
        assert results[0].angle == 0
        assert results[0].psm == 11

        # Result 1: Loader1, psm 11, angle 90
        assert results[1].loader == "Loader1"
        assert results[1].match == mock_match2
        assert results[1].angle == 90
        assert results[1].psm == 11

        # Result 2: Loader1, psm 6, angle 0
        assert results[2].loader == "Loader1"
        assert results[2].match == mock_match3
        assert results[2].angle == 0
        assert results[2].psm == 6

        # Result 3: Loader1, psm 6, angle 90
        assert results[3].loader == "Loader1"
        assert results[3].match == mock_match4
        assert results[3].angle == 90
        assert results[3].psm == 6

        # Result 4: Loader2, psm 11, angle 0
        assert results[4].loader == "Loader2"
        assert results[4].match == mock_match5
        assert results[4].angle == 0
        assert results[4].psm == 11

        # Result 5: Loader2, psm 6, angle 0
        assert results[5].loader == "Loader2"
        assert results[5].match == mock_match6
        assert results[5].angle == 0
        assert results[5].psm == 6

        assert processor.find_single.call_count == 6
        assert mock_format_elapsed_time.call_count == 6

    @patch("hope_ocr.ocr.engine.time_it")
    @patch("hope_ocr.ocr.engine.format_elapsed_time", return_value="2s")
    def test_processor_find_text_best_mode_success(
        self, mock_format_elapsed_time, mock_time_it, mock_ts_config, mock_cv2_config
    ):
        processor = Processor(mock_ts_config, mock_cv2_config)

        mock_loader = MagicMock()
        mock_loader.__class__.__name__ = "TestLoader"
        mock_loader.rotate.return_value = [(MagicMock(spec=Image.Image), 0), (MagicMock(spec=Image.Image), 90)]
        processor.loaders = [mock_loader]

        mock_reader = MagicMock()
        mock_reader.config = MagicMock()
        processor.reader = mock_reader

        mock_match1 = MagicMock(distance=0.5)
        mock_match2 = MagicMock(distance=0.1) # Best match
        processor.find_single = MagicMock(side_effect=[
            ("text1", mock_match1),
            ("text2", mock_match2),
            ("text3", MagicMock(distance=0.3)),
            ("text4", MagicMock(distance=0.4)),
        ])

        mock_time_it_instance = MagicMock()
        mock_time_it_instance.__enter__.return_value.get_partial.side_effect = [i * 0.1 for i in range(1, 101)] # Sufficiently long list
        mock_time_it.return_value = mock_time_it_instance

        original_image = MagicMock(spec=Image.Image)
        target_text = "target"

        results = list(processor.find_text(original_image, target_text, mode=MatchMode.BEST))

        assert len(results) == 1
        result = results[0]
        assert result.loader == "TestLoader"
        assert result.match == mock_match2
        assert result.angle == 90
        assert result.psm == 11
        assert result.time == "2s" # Final time

    @patch("hope_ocr.ocr.engine.time_it")
    @patch("hope_ocr.ocr.engine.format_elapsed_time", return_value="2s")
    def test_processor_find_text_best_mode_zero_distance_stop(
        self, mock_format_elapsed_time, mock_time_it, mock_ts_config, mock_cv2_config
    ):
        processor = Processor(mock_ts_config, mock_cv2_config)

        mock_loader = MagicMock()
        mock_loader.__class__.__name__ = "TestLoader"
        mock_loader.rotate.return_value = [(MagicMock(spec=Image.Image), 0), (MagicMock(spec=Image.Image), 90)]
        processor.loaders = [mock_loader]

        mock_reader = MagicMock()
        mock_reader.config = MagicMock()
        processor.reader = mock_reader

        mock_match1 = MagicMock(distance=0.5)
        mock_match2 = MagicMock(distance=0.0) # Zero distance, should stop
        processor.find_single = MagicMock(side_effect=[
            ("text1", mock_match1),
            ("text2", mock_match2),
            ("text3", MagicMock(distance=0.3)), # Added
            ("text4", MagicMock(distance=0.4)), # Added
        ])

        mock_time_it_instance = MagicMock()
        mock_time_it_instance.__enter__.return_value.get_partial.side_effect = [i * 0.1 for i in range(1, 101)] # Sufficiently long list
        mock_time_it.return_value = mock_time_it_instance

        original_image = MagicMock(spec=Image.Image)
        target_text = "target"

        results = list(processor.find_text(original_image, target_text, mode=MatchMode.BEST))

        assert len(results) == 1
        result = results[0]
        assert result.loader == "TestLoader"
        assert result.match == mock_match2
        assert result.angle == 90
        assert result.psm == 11
        assert result.time == "2s"

        assert processor.find_single.call_count == 2 # Only two calls before stopping

    @patch("hope_ocr.ocr.engine.time_it")
    @patch("hope_ocr.ocr.engine.format_elapsed_time", return_value="1s")
    def test_processor_find_text_debug_mode(
        self, mock_format_elapsed_time, mock_time_it, mock_ts_config, mock_cv2_config
    ):
        processor = Processor(mock_ts_config, mock_cv2_config)

        mock_loader = MagicMock()
        mock_loader.__class__.__name__ = "TestLoader"
        mock_loader.rotate.return_value = [(MagicMock(spec=Image.Image), 0)]
        processor.loaders = [mock_loader]

        mock_reader = MagicMock()
        mock_reader.config = MagicMock()
        processor.reader = mock_reader

        mock_match = MagicMock()
        processor.find_single = MagicMock(return_value=("extracted text", mock_match))

        mock_time_it_instance = MagicMock()
        mock_time_it_instance.__enter__.return_value.get_partial.return_value = 1.0
        mock_time_it.return_value = mock_time_it_instance

        original_image = MagicMock(spec=Image.Image)
        target_text = "target"

        results = list(processor.find_text(original_image, target_text, mode=MatchMode.FIRST, debug=True))

        assert len(results) == 1
        assert processor.debug_info.iterations[0] == results[0]

    @patch("hope_ocr.ocr.engine.time_it")
    @patch("hope_ocr.ocr.engine.format_elapsed_time", return_value="1s")
    def test_processor_find_text_search_test_pattern(
        self, mock_format_elapsed_time, mock_time_it, mock_ts_config, mock_cv2_config
    ):
        processor = Processor(mock_ts_config, mock_cv2_config)

        mock_loader = MagicMock()
        mock_loader.__class__.__name__ = "TestLoader"
        mock_loader.rotate.return_value = [(MagicMock(spec=Image.Image), 0)]
        processor.loaders = [mock_loader]

        mock_reader = MagicMock()
        mock_reader.config = MagicMock()
        processor.reader = mock_reader

        mock_match = MagicMock()
        processor.find_single = MagicMock(return_value=("extracted text", mock_match))

        mock_time_it_instance = MagicMock()
        mock_time_it_instance.__enter__.return_value.get_partial.return_value = 1.0
        mock_time_it.return_value = mock_time_it_instance

        original_image = MagicMock(spec=Image.Image)
        target_text = SEARCH_TEST_PATTERN

        results = list(processor.find_text(original_image, target_text, mode=MatchMode.FIRST))

        assert len(results) == 1
        result = results[0]
        assert isinstance(result, SearchInfo)
        assert result.loader == "TestLoader"
        assert result.match == mock_match
        assert result.text == "extracted text"
        assert result.angle == 0
        assert result.psm == 11

    @patch("hope_ocr.ocr.engine.time_it")
    @patch("hope_ocr.ocr.engine.format_elapsed_time", return_value="1s")
    def test_processor_process_success(
        self, mock_format_elapsed_time, mock_time_it, mock_ts_config, mock_cv2_config
    ):
        processor = Processor(mock_ts_config, mock_cv2_config)

        mock_loader = MagicMock()
        mock_loader.__class__.__name__ = "TestLoader"
        mock_loader.load.return_value = MagicMock(spec=Image.Image) # Mock loaded image
        mock_loader.load.return_value.rotate.return_value = MagicMock(spec=Image.Image) # Mock rotated image
        processor.loaders = [mock_loader]

        mock_reader = MagicMock()
        mock_reader.extract.return_value = "processed text"
        processor.reader = mock_reader

        mock_time_it_instance = MagicMock()
        mock_time_it_instance.__enter__.return_value.human = "0.5s"
        mock_time_it.return_value = mock_time_it_instance

        filepath = "test_file.png"

        results = list(processor.process(filepath))

        assert len(results) == 1
        result = results[0]
        assert isinstance(result, ScanEntryInfo)
        assert result.loader == "TestLoader"
        assert result.text == "processed text"
        assert result.error == ""
        assert result.time == "0.5s"

        mock_loader.load.assert_called_once_with(filepath)
        mock_reader.extract.assert_called_once_with(mock_loader.load.return_value)
        mock_loader.load.return_value.rotate.assert_not_called()

    @patch("hope_ocr.ocr.engine.time_it")
    @patch("hope_ocr.ocr.engine.format_elapsed_time", return_value="1s")
    def test_processor_process_success_with_rotation(
        self, mock_format_elapsed_time, mock_time_it, mock_ts_config, mock_cv2_config
    ):
        processor = Processor(mock_ts_config, mock_cv2_config)

        mock_loader = MagicMock()
        mock_loader.__class__.__name__ = "TestLoader"
        mock_loaded_image = MagicMock(spec=Image.Image)
        mock_rotated_image = MagicMock(spec=Image.Image)
        mock_loaded_image.rotate.return_value = mock_rotated_image # Mock rotate method
        mock_loader.load.return_value = mock_loaded_image
        processor.loaders = [mock_loader]

        mock_reader = MagicMock()
        mock_reader.config = MagicMock()
        processor.reader = mock_reader

        mock_time_it_instance = MagicMock()
        mock_time_it_instance.__enter__.return_value.human = "0.7s"
        mock_time_it.return_value = mock_time_it_instance

        filepath = "test_file.png"
        rotate_angle = 90

        results = list(processor.process(filepath, rotate=rotate_angle))

        assert len(results) == 1
        result = results[0]
        assert isinstance(result, ScanEntryInfo)
        assert result.loader == "TestLoader"
        assert result.text == mock_reader.extract.return_value # Changed this line
        assert result.error == ""
        assert result.time == "0.7s"

        mock_loader.load.assert_called_once_with(filepath)
        mock_loaded_image.rotate.assert_called_once_with(rotate_angle, expand=True)
        mock_reader.extract.assert_called_once_with(mock_rotated_image)

    @patch("hope_ocr.ocr.engine.time_it")
    @patch("hope_ocr.ocr.engine.format_elapsed_time", return_value="1s")
    def test_processor_process_error_handling(
        self, mock_format_elapsed_time, mock_time_it, mock_ts_config, mock_cv2_config
    ):
        processor = Processor(mock_ts_config, mock_cv2_config)

        mock_loader = MagicMock()
        mock_loader.__class__.__name__ = "TestLoader"
        mock_loader.load.side_effect = InvalidImageError("Broken image") # Mock load to raise error
        processor.loaders = [mock_loader]

        mock_reader = MagicMock()
        processor.reader = mock_reader

        mock_time_it_instance = MagicMock()
        mock_time_it_instance.__enter__.return_value.human = "0.1s"
        mock_time_it.return_value = mock_time_it_instance

        filepath = "test_file.png"

        results = list(processor.process(filepath))

        assert len(results) == 1
        result = results[0]
        assert isinstance(result, ScanEntryInfo)
        assert result.loader == "TestLoader"
        assert result.text == ""
        assert result.error == "InvalidImageError: Broken image"
        assert result.time == "0.1s"

        mock_loader.load.assert_called_once_with(filepath)
        mock_reader.extract.assert_not_called()