"""Point features that are one aggregate over the window's values."""

from __future__ import annotations

from attrs import frozen
from ibis import ir

from .base import PointFeature, Points

__all__ = ["ApproxMedian", "Count", "Max", "Mean", "Min", "StandardDeviation", "Sum"]


@frozen
class ApproxMedian(PointFeature):
    """Approximate median of the window's non-null values, e.g. `[1, 9, 5]` → `5`.

    Approximate on DuckDB and Trino; always between the window's min and max.
    """

    def reduce(self, points: Points) -> ir.Value:
        return points.values.approx_median()


@frozen
class Count(PointFeature):
    """Number of non-null values in the window, e.g. `[1, None, 4]` → `2`."""

    def reduce(self, points: Points) -> ir.Value:
        return points.values.count()


@frozen
class Max(PointFeature):
    """Largest non-null value in the window, e.g. `[3, None, 1, 2]` → `3`."""

    def reduce(self, points: Points) -> ir.Value:
        return points.values.max()


@frozen
class Mean(PointFeature):
    """Mean of the window's non-null values, e.g. `[1, None, 4]` → `2.5`."""

    def reduce(self, points: Points) -> ir.Value:
        return points.values.mean()


@frozen
class Min(PointFeature):
    """Smallest non-null value in the window, e.g. `[3, None, 1, 2]` → `1`."""

    def reduce(self, points: Points) -> ir.Value:
        return points.values.min()


@frozen
class StandardDeviation(PointFeature):
    """Sample standard deviation of the window's non-null values.

    E.g. `[1, None, 3]` → `1.414…` (`sqrt(2)`). Null with fewer than two values.
    """

    def reduce(self, points: Points) -> ir.Value:
        return points.values.std()


@frozen
class Sum(PointFeature):
    """Sum of the window's non-null values, e.g. `[1, None, 4]` → `5`."""

    def reduce(self, points: Points) -> ir.Value:
        return points.values.sum()
