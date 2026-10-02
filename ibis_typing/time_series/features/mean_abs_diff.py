"""The `MeanAbsDiff` point feature."""

from __future__ import annotations

from typing import ClassVar

from attrs import frozen
from ibis import ir

from .base import PointFeature, Points

__all__ = ["MeanAbsDiff"]


@frozen
class MeanAbsDiff(PointFeature):
    """Mean absolute step between consecutive values in the window.

    E.g. `[1, 2, 4, 1]` → `(1 + 2 + 3) / 3 = 2`. Steps touching a null are
    skipped, and a one-point window is null.
    """

    uses_lag: ClassVar[bool] = True

    @property
    def name(self) -> str:
        return "mean_abs_diff"

    def reduce(self, points: Points) -> ir.Value:
        return (points.values - points.previous_values).abs().mean()
