"""The `StandardDeviation` point feature."""

from __future__ import annotations

from attrs import frozen
from ibis import ir

from .base import PointFeature, Points

__all__ = ["StandardDeviation"]


@frozen
class StandardDeviation(PointFeature):
    """Sample standard deviation of the window's non-null values.

    E.g. `[1, None, 3]` → `1.414…` (`sqrt(2)`). Null with fewer than two values.
    """

    @property
    def name(self) -> str:
        return "standard_deviation"

    def reduce(self, points: Points) -> ir.Value:
        return points.values.std()
