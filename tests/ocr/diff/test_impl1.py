import pytest

from hope_documents.ocr.diff.common import Match
from hope_documents.ocr.diff.impl1 import find_similar, levenshtein_distance


@pytest.mark.parametrize(
    ("s1", "s2", "expected_distance"),
    [
        ("", "", 0),
        ("abc", "abc", 0),
        ("abc", "", 3),
        ("", "abc", 3),
        ("kitten", "sitting", 3),  # 1 substitution, 1 insertion, 1 substitution
        ("saturday", "sunday", 3),
        ("flaw", "lawn", 2),
    ],
)
def test_levenshtein_distance(s1, s2, expected_distance):
    """Test that levenshtein_distance calculates the correct edit distance."""
    assert levenshtein_distance(s1, s2) == expected_distance
    # The function should be symmetrical
    assert levenshtein_distance(s2, s1) == expected_distance


# --- Tests for find_similar ---


def test_find_similar_exact_match():
    """Test a simple exact match."""
    match = find_similar("world", "Hello world", max_distance=0)
    assert match == Match(text="world", distance=0)


def test_find_similar_no_match():
    """Test when no match is found within the max_distance."""
    assert find_similar("galaxy", "Hello world", max_distance=2) is None


def test_find_similar_with_distance():
    """Test finding a match that is within the allowed distance."""
    # "wrold" is 2 substitutions away from "world" after normalization
    match = find_similar("wrold", "Hello world", max_distance=2)
    assert match == Match(text="world", distance=2)


def test_find_similar_with_separators():
    """Test that separators in the pattern and text are ignored."""
    match = find_similar("ID-123", "ID 123", max_distance=0)
    assert match == Match(text="ID 123", distance=0)

    match = find_similar("ID 123", "ID-123", max_distance=0)
    assert match == Match(text="ID-123", distance=0)


def test_find_similar_with_homoglyphs():
    """Test that homoglyphs are correctly normalized and matched."""
    # 'O' and '0' are homoglyphs
    match = find_similar("HELLO", "HELL0 W0RLD", max_distance=0)
    assert match == Match(text="HELL0", distance=0)

    # '1' and 'I' are homoglyphs
    match = find_similar("ID-123", "ID-l23", max_distance=0)
    assert match == Match(text="ID-l23", distance=0)


def test_find_similar_returns_best_match():
    """Test that the function returns the match with the lowest distance."""
    # The text contains "wrold" (dist 1) and "world" (dist 0)
    text = "Hello wrold, this is the world."
    # We search for "world" with a max distance of 1
    match = find_similar("world", text, max_distance=1)
    # It should find the exact match, not the one with a distance of 1
    assert match == Match(text="world", distance=0)


def test_find_similar_empty_pattern():
    """Test that an empty pattern returns None."""
    assert find_similar("", "some text") is None


def test_find_similar_original_text_extraction():
    """Test that the matched text is correctly extracted from the original string."""
    text = "My ID is: ID-123 / ABC"
    # Search for a pattern that will match across separators
    match = find_similar("123ABC", text, max_distance=0)
    # The extracted text should include the original separators
    assert match == Match(text="123 / ABC", distance=0)
