import pytest

from hope_documents.archive.region import BoundingBox
from hope_documents.llm.prompt import PromptBuilder


def test_build_contains_all_sections():
    bb = BoundingBox.from_rect(10, 10, 20, 20)
    prompt = (
        PromptBuilder()
        .with_role()
        .with_field_hint("first_name")
        .with_rules()
        .with_output_format()
        .with_region_hint(bb, (200, 200))
        .build()
    )
    assert "extracting a single field" in prompt
    assert "first_name" in prompt
    assert "confidence=0" in prompt
    assert '"confidence"' in prompt
    assert "area of the document" in prompt


def test_build_raises_if_no_sections():
    with pytest.raises(ValueError):
        PromptBuilder().build()


def test_region_hint_upper_left():
    bb = BoundingBox.from_rect(10, 10, 20, 20)  # centre ~(20,20), image 200x200 → upper-left
    prompt = PromptBuilder().with_role().with_region_hint(bb, (200, 200)).build()
    assert "upper" in prompt
    assert "left" in prompt


def test_region_hint_lower_right():
    bb = BoundingBox.from_rect(150, 150, 30, 30)  # centre ~(165,165), image 200x200 → lower-right
    prompt = PromptBuilder().with_role().with_region_hint(bb, (200, 200)).build()
    assert "lower" in prompt
    assert "right" in prompt


def test_region_hint_zero_area_skipped():
    bb = BoundingBox.from_rect(50, 50, 0, 0)  # zero area
    prompt = PromptBuilder().with_role().with_region_hint(bb, (200, 200)).build()
    assert "area of the document" not in prompt
