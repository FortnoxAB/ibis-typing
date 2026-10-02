"""The `Min` point feature."""

from __future__ import annotations

from attrs import frozen
from ibis import ir

from .base import PointFeature, Points

__all__ = ["Min"]


@frozen
class Min(PointFeature):
    """Smallest non-null value in the window, e.g. `[3, None, 1, 2]` → `1`."""

    @property
    def name(self) -> str:
        return "min"

    def reduce(self, points: Points) -> ir.Value:
        return points.values.min()
