import json

import pytest

from factories.documents import DocumentAttributeFactory
from hope_ocr.archive.models import DocumentAttribute
from hope_ocr.archive.region import BoundingBox, BoundingBoxField, Point


def test_point_negative_x_raises():
    with pytest.raises(ValueError):
        Point(x=-1, y=0)


def test_point_negative_y_raises():
    with pytest.raises(ValueError):
        Point(x=0, y=-1)


def test_bounding_box_from_rect():
    bb = BoundingBox.from_rect(10, 20, 100, 50)
    assert bb.top_left == Point(10, 20)
    assert bb.top_right == Point(110, 20)
    assert bb.bottom_right == Point(110, 70)
    assert bb.bottom_left == Point(10, 70)


def test_bounding_box_width_height():
    bb = BoundingBox.from_rect(10, 20, 100, 50)
    assert bb.width == 100
    assert bb.height == 50


def test_bounding_box_to_dict_from_dict_round_trip():
    original = BoundingBox.from_rect(10, 20, 100, 50)
    assert BoundingBox.from_dict(original.to_dict()) == original


def test_bounding_box_field_from_db_value_none():
    field = BoundingBoxField()
    assert field.from_db_value(None, None, None) is None


def test_bounding_box_field_from_db_value_dict_returns_bounding_box():
    field = BoundingBoxField()
    bb = BoundingBox.from_rect(0, 0, 50, 50)
    result = field.from_db_value(json.dumps(bb.to_dict()), None, None)
    assert isinstance(result, BoundingBox)
    assert result == bb


def test_bounding_box_field_get_prep_value_does_not_raise():
    """BoundingBox must be converted to dict before JSON encoding; without the override this raises TypeError."""
    field = BoundingBoxField()
    bb = BoundingBox.from_rect(0, 0, 50, 50)
    result = field.get_prep_value(bb)
    assert result is not None


def test_bounding_box_field_value_from_object_returns_dict():
    """Regression: admin inline formsets call value_from_object; BoundingBox must not be returned as-is."""
    field = DocumentAttribute._meta.get_field("region")
    da = DocumentAttribute()
    da.region = BoundingBox.from_rect(5, 10, 100, 200)
    result = field.value_from_object(da)
    assert isinstance(result, dict)
    assert result == BoundingBox.from_rect(5, 10, 100, 200).to_dict()


@pytest.mark.django_db
def test_document_attribute_region_db_round_trip():
    bb = BoundingBox.from_rect(10, 20, 100, 50)
    da = DocumentAttributeFactory.create(region=bb)
    da.refresh_from_db()
    assert isinstance(da.region, BoundingBox)
    assert da.region == bb
