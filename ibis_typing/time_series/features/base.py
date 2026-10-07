"""Base classes for features that reduce one window of one column to one value."""

from __future__ import annotations

import abc
from typing import ClassVar

from attrs import frozen
from ibis import ir

from ibis_typing.naming import snake_case

__all__ = [
    "PointFeature",
    "Points",
    "SpectralFeature",
    "Spectrum",
    "TimeSeriesFeature",
]


class TimeSeriesFeature(abc.ABC):
    """A feature of one value column over one trailing window."""

    @property
    def name(self) -> str:
        """Output column suffix, the snake_case class name, e.g. `"mean_abs_diff"`.

        Override to change it, or to include parameters.
        """
        return snake_case(type(self).__name__)


class PointFeature(TimeSeriesFeature):
    """Aggregates the points of a window into one value.

    `reduce` gets the window's points as columns (`Points`) and returns one
    aggregate over them, e.g. `points.values.sum()`.

    By default it runs as a SQL window function and may only aggregate `values`.
    Set `uses_lag = True` to also read `previous_values`. Set `windowable = False`
    to also read `position` and `steps_from_newest`; each window is then expanded
    into rows and grouped, which costs more.

    To add a feature, subclass this with `@frozen` and define `reduce`.
    """

    uses_lag: ClassVar[bool] = False
    windowable: ClassVar[bool] = True

    @abc.abstractmethod
    def reduce(self, points: Points) -> ir.Value: ...


class SpectralFeature(TimeSeriesFeature):
    """Aggregates the magnitude spectrum of a window into one value.

    `reduce` gets one row per frequency bin of the window's real DFT (`Spectrum`)
    and returns one aggregate over the bins, e.g. `spectrum.magnitude.max()`.
    The window's least-squares line is removed first, so neither level nor trend
    dominates. Windows with a null value, fewer than 3 points or nothing left
    after detrending are null.

    To add a feature, subclass this with `@frozen` and define `reduce`.
    """

    @abc.abstractmethod
    def reduce(self, spectrum: Spectrum) -> ir.Value: ...


@frozen
class Points:
    """Columns of one window, one row per point.

    `previous_values_column` and `position_column` are set by the engine; read
    them through `previous_values`, `position` and `steps_from_newest`.
    """

    values: ir.NumericColumn
    window_size: int
    feature: PointFeature
    previous_values_column: ir.NumericColumn | None = None
    position_column: ir.IntegerColumn | None = None

    @property
    def previous_values(self) -> ir.NumericColumn:
        """Value of the previous point, null for the window's oldest point."""
        if self.previous_values_column is None:
            raise TypeError(self._unavailable("previous_values", "uses_lag = True"))
        return self.previous_values_column

    @property
    def position(self) -> ir.IntegerColumn:
        """Position in the window: 0 for the oldest point."""
        if self.position_column is None:
            raise TypeError(self._unavailable("position", "windowable = False"))
        return self.position_column

    @property
    def steps_from_newest(self) -> ir.IntegerColumn:
        """Steps back from the window's newest point: 0 for the newest point."""
        if self.position_column is None:
            raise TypeError(
                self._unavailable("steps_from_newest", "windowable = False")
            )
        return -self.position_column + (self.window_size - 1)

    def _unavailable(self, attribute: str, setting: str) -> str:
        name = type(self.feature).__name__
        return f"{name} uses Points.{attribute}: set {setting} on {name}."


@frozen
class Spectrum:
    """Columns of one window's spectrum, one row per `frequency_bin`.

    `frequency_bin` runs over `0 .. window_size // 2`, `frequency` is
    `frequency_bin * sampling_frequency / window_size` and `cumulative_magnitude`
    sums `magnitude` up to and including the bin.
    """

    frequency_bin: ir.IntegerColumn
    frequency: ir.FloatingColumn
    magnitude: ir.FloatingColumn
    cumulative_magnitude: ir.FloatingColumn
    total_magnitude: ir.FloatingColumn
    window_size: int
