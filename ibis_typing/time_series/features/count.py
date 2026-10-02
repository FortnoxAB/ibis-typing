"""The `Count` point feature."""

from __future__ import annotations

from attrs import frozen
from ibis import ir

from .base import PointFeature, Points

__all__ = ["Count"]


@frozen
class Count(PointFeature):
    """Number of non-null values in the window, e.g. `[1, None, 4]` → `2`."""

    @property
    def name(self) -> str:
        return "count"

    def reduce(self, points: Points) -> ir.Value:
        return points.values.count()
