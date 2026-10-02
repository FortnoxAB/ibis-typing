"""The `ApproxMedian` point feature."""

from __future__ import annotations

from attrs import frozen
from ibis import ir

from .base import PointFeature, Points

__all__ = ["ApproxMedian"]


@frozen
class ApproxMedian(PointFeature):
    """Approximate median of the window's non-null values, e.g. `[1, 9, 5]` → `5`.

    Approximate on DuckDB and Trino; always between the window's min and max.
    """

    @property
    def name(self) -> str:
        return "approx_median"

    def reduce(self, points: Points) -> ir.Value:
        return points.values.approx_median()
