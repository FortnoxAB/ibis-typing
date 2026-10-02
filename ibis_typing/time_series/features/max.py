"""The `Max` point feature."""

from __future__ import annotations

from attrs import frozen
from ibis import ir

from .base import PointFeature, Points

__all__ = ["Max"]


@frozen
class Max(PointFeature):
    """Largest non-null value in the window, e.g. `[3, None, 1, 2]` → `3`."""

    @property
    def name(self) -> str:
        return "max"

    def reduce(self, points: Points) -> ir.Value:
        return points.values.max()
