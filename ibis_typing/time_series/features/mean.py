"""The `Mean` point feature."""

from __future__ import annotations

from attrs import frozen
from ibis import ir

from .base import PointFeature, Points

__all__ = ["Mean"]


@frozen
class Mean(PointFeature):
    """Mean of the window's non-null values, e.g. `[1, None, 4]` → `2.5`."""

    @property
    def name(self) -> str:
        return "mean"

    def reduce(self, points: Points) -> ir.Value:
        return points.values.mean()
