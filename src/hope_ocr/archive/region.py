import dataclasses
from typing import Any

from django.db import models


@dataclasses.dataclass(frozen=True)
class Point:
    x: float
    y: float

    def __post_init__(self) -> None:
        if self.x < 0 or self.y < 0:
            raise ValueError("Point coordinates must be non-negative.")


@dataclasses.dataclass(frozen=True)
class BoundingBox:
    top_left: Point
    top_right: Point
    bottom_right: Point
    bottom_left: Point

    @classmethod
    def from_rect(cls, x: float, y: float, width: float, height: float) -> "BoundingBox":
        return cls(
            top_left=Point(x, y),
            top_right=Point(x + width, y),
            bottom_right=Point(x + width, y + height),
            bottom_left=Point(x, y + height),
        )

    @classmethod
    def from_dict(cls, data: dict) -> "BoundingBox":
        return cls(**{k: Point(**v) for k, v in data.items()})

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)

    @property
    def width(self) -> float:
        return self.top_right.x - self.top_left.x

    @property
    def height(self) -> float:
        return self.bottom_left.y - self.top_left.y


class BoundingBoxField(models.JSONField):
    def from_db_value(self, value: Any, expression: Any, connection: Any) -> BoundingBox | None:
        result = super().from_db_value(value, expression, connection)
        if result is None or isinstance(result, BoundingBox):
            return result
        return BoundingBox.from_dict(result)

    def to_python(self, value: Any) -> BoundingBox | None:
        result = super().to_python(value)
        if result is None or isinstance(result, BoundingBox):
            return result
        return BoundingBox.from_dict(result)

    def get_prep_value(self, value: Any) -> Any:
        if isinstance(value, BoundingBox):
            value = value.to_dict()
        return super().get_prep_value(value)

    def value_from_object(self, obj: Any) -> Any:
        value = super().value_from_object(obj)
        if isinstance(value, BoundingBox):
            return value.to_dict()
        return value
