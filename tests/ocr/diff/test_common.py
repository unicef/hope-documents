import pytest

from hope_documents.ocr.diff.common import _normalize_homoglyphs


@pytest.mark.parametrize(
    ("input_str", "expected_str"),
    [
        # Test with characters that have homoglyphs
        ("o15z8a-", "01528A-"),
        ("OIlSZb@/.", "011528A--"),
        # Test with mixed characters (mapped and unmapped)
        ("Hello World 123", "HE110 W0R1D 123"),
        # Test with characters that are not in the map (should be uppercased)
        ("python", "PYTH0N"),
        # Test with an empty string
        ("", ""),
        # Test a real-world example with mixed case and symbols
        ("ID-123/S.A", "1D-123-5-A"),
    ],
)
def test_normalize_homoglyphs(input_str, expected_str):
    """Test that _normalize_homoglyphs correctly normalizes strings."""
    assert _normalize_homoglyphs(input_str) == expected_str
