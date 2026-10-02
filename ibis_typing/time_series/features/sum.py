"""The `Sum` point feature."""

from __future__ import annotations

from attrs import frozen
from ibis import ir

from .base import PointFeature, Points

__all__ = ["Sum"]


@frozen
class Sum(PointFeature):
    """Sum of the window's non-null values, e.g. `[1, None, 4]` → `5`."""

    @property
    def name(self) -> str:
        return "sum"

    def reduce(self, points: Points) -> ir.Value:
        return points.values.sum()
