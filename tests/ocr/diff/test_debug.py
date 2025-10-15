from hope_documents.ocr.diff.common import Match
from hope_documents.ocr.diff.impl1 import find_similar


def test_find_similar_with_distance_debug():
    """Test finding a match that is within the allowed distance."""
    # "wrold" is 2 substitutions away from "world" after normalization
    match = find_similar("wrold", "Hello world", max_distance=2)
    assert match == Match(text="world", distance=2)
