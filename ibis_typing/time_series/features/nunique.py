"""The `NUnique` point feature."""

from __future__ import annotations

from typing import ClassVar

from attrs import frozen
from ibis import ir

from .base import PointFeature, Points

__all__ = ["NUnique"]


@frozen
class NUnique(PointFeature):
    """Number of distinct non-null values in the window, e.g. `[1, 2, 2, None]` → `2`.

    Sets `windowable = False`, so each window is expanded into rows and grouped:
    `COUNT(DISTINCT)` over a window frame is not supported on every backend.
    """

    windowable: ClassVar[bool] = False

    def reduce(self, points: Points) -> ir.Value:
        return points.values.nunique()
