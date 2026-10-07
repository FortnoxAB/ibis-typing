"""Query stages of `TimeSeriesFeatureExtraction`.

`prepare` numbers the rows of each series by `order_by` as `POSITION` and casts
each value column to `float64` as `value_column(column)`; every later stage orders
by `POSITION` and reads the values from `value_column(column)`.
"""

from __future__ import annotations

import math
from collections.abc import Callable, Mapping, Sequence
from typing import cast

import ibis
from ibis import Table, ir

from .. import ibis_ops
from ..ibis_api import IfElse
from ..ibis_utils import Aggregate
from .features import PointFeature, Points, SpectralFeature, Spectrum, TimeSeriesFeature

__all__ = [
    "FREQUENCY",
    "FREQUENCY_BIN",
    "POSITION",
    "POSITION_IN_WINDOW",
    "WINDOW_END",
    "ZERO_TOLERANCE",
    "expand",
    "expanded_point_features",
    "join_back",
    "prepare",
    "previous_values_column",
    "spectral_features",
    "value_column",
    "window_features",
]

type Naming = Callable[[str, TimeSeriesFeature, int], str]

# Position of a row in its series: 0 for the oldest row.
POSITION = "__ts_position"
# `POSITION` of the newest row of an expanded window.
WINDOW_END = "__ts_window_end"
# Position of a point in its expanded window: 0 for the oldest point.
POSITION_IN_WINDOW = "__ts_position_in_window"
FREQUENCY_BIN = "__ts_frequency_bin"
FREQUENCY = "__ts_frequency"
# `POSITION` of the newest row of a series.
_LAST_POSITION = "__ts_last_position"
# Positions from a point to the end of a window containing it.
_OFFSET = "__ts_offset"

# Below this magnitude relative to the window's scale, a detrended window is zero:
# about 1e4 times float64 rounding (~2.2e-16), so a constant or linear window is
# zero while a variation of 1e-9 of the level is not.
ZERO_TOLERANCE = 1e-12


def value_column(column: str) -> str:
    """Helper column with the values of `column` as `float64`."""
    return f"__ts_value__{column}"


def previous_values_column(column: str) -> str:
    """Helper column with the value of `column` at the previous position."""
    return f"__ts_previous_values__{column}"


def _floating(table: Table, name: str) -> ir.FloatingColumn:
    column: ir.Column = table[name]
    return cast(ir.FloatingColumn, column)


def _integer(table: Table, name: str) -> ir.IntegerColumn:
    column: ir.Column = table[name]
    return cast(ir.IntegerColumn, column)


def _null_unless(condition: ir.BooleanValue, value: ir.Value) -> ir.Value:
    """`value` where `condition` holds, otherwise null of the same type."""
    null: ir.Value = ibis.null(value.type())
    return condition @ IfElse(value, null)


def prepare(
    table: Table,
    *,
    keys: Sequence[str],
    order_by: str,
    columns: Sequence[str],
    uses_lag: bool,
) -> Table:
    """Add `POSITION`, the `float64` values and, if `uses_lag`, previous values.

    Casting once keeps every later stage, e.g. a difference of `uint8` values,
    from overflowing.
    """
    series = ibis.window(group_by=list(keys), order_by=table[order_by])
    prepared = table.mutate(
        **{POSITION: ibis.row_number().over(series)},
        **{value_column(column): table[column].cast("float64") for column in columns},
    )
    if not uses_lag:
        return prepared
    return prepared.mutate(
        **{
            previous_values_column(column): _floating(prepared, value_column(column))
            .lag()
            .over(series)
            for column in columns
        }
    )


def window_features(  # noqa: PLR0913
    table: Table,
    *,
    keys: Sequence[str],
    columns: Sequence[str],
    features: Sequence[PointFeature],
    window_size: int,
    naming: Naming,
) -> Mapping[str, ir.Value]:
    """Windowable point features of each row's trailing window, as SQL windows."""
    position = _integer(table, POSITION)
    complete = position >= ibis.literal(window_size - 1)
    frame = ibis.window(
        group_by=list(keys),
        order_by=position,
        preceding=window_size - 1,
        following=0,
    )
    # Skip the window's oldest point, whose previous value lies outside the window.
    lag_frame = ibis.window(
        group_by=list(keys),
        order_by=position,
        preceding=max(window_size - 2, 0),
        following=0,
    )

    def value(column: str, feature: PointFeature) -> ir.Value:
        values = _floating(table, value_column(column))
        if feature.uses_lag:
            points = Points(
                values=values,
                window_size=window_size,
                feature=feature,
                previous_values_column=_floating(table, previous_values_column(column)),
            )
            if window_size == 1:
                return ibis.null(feature.reduce(points).type())
            return _null_unless(complete, feature.reduce(points).over(lag_frame))
        points = Points(values=values, window_size=window_size, feature=feature)
        return _null_unless(complete, feature.reduce(points).over(frame))

    return {
        naming(column, feature, window_size): value(column, feature)
        for column in columns
        for feature in features
    }


def expand(
    table: Table,
    *,
    keys: Sequence[str],
    columns: Sequence[str],
    window_size: int,
    uses_lag: bool,
) -> Table:
    """One row per point of each complete window, ending at `WINDOW_END`.

    Each point is copied to the windows ending 0 .. `window_size - 1` positions
    after it, so the cost is linear in the series length and needs no join.
    """
    values = [value_column(column) for column in columns]
    # Ordered: DuckDB rewrites an unordered window aggregate into a self join,
    # which fails to bind below the spectral window functions.
    series = ibis.window(group_by=list(keys), order_by=_integer(table, POSITION))
    points = table.select(
        *keys,
        POSITION,
        *values,
        **{_LAST_POSITION: _integer(table, POSITION).max().over(series)},
    )
    offsets = ibis_ops.literal_table(
        f"__ts_offsets_{window_size}",
        [(offset,) for offset in range(window_size)],
        ibis.schema({_OFFSET: "int64"}),
    )
    copies = points.cross_join(offsets)
    offset = _integer(copies, _OFFSET)
    window_end = _integer(copies, POSITION) + offset
    in_complete_window = copies.filter(
        window_end >= ibis.literal(window_size - 1),
        window_end <= _integer(copies, _LAST_POSITION),
    )
    offset = _integer(in_complete_window, _OFFSET)
    expanded = in_complete_window.select(
        *keys,
        **{WINDOW_END: _integer(in_complete_window, POSITION) + offset},
        **{value: in_complete_window[value] for value in values},
        **{POSITION_IN_WINDOW: ibis.literal(window_size - 1) - offset},
    )
    if not uses_lag:
        return expanded
    window = ibis.window(
        group_by=[*keys, WINDOW_END], order_by=_integer(expanded, POSITION_IN_WINDOW)
    )
    return expanded.mutate(
        **{
            previous_values_column(column): _floating(expanded, value_column(column))
            .lag()
            .over(window)
            for column in columns
        }
    )


def expanded_point_features(  # noqa: PLR0913
    expanded: Table,
    *,
    keys: Sequence[str],
    columns: Sequence[str],
    features: Sequence[PointFeature],
    window_size: int,
    naming: Naming,
) -> Table:
    """Point features of each expanded window, one row per `WINDOW_END`."""

    def points(column: str, feature: PointFeature) -> Points:
        previous_values = (
            _floating(expanded, previous_values_column(column))
            if feature.uses_lag
            else None
        )
        return Points(
            values=_floating(expanded, value_column(column)),
            window_size=window_size,
            feature=feature,
            previous_values_column=previous_values,
            position_column=_integer(expanded, POSITION_IN_WINDOW),
        )

    return expanded @ Aggregate(
        by=[*keys, WINDOW_END],
        expr={
            naming(column, feature, window_size): feature.reduce(
                points(column, feature)
            )
            for column in columns
            for feature in features
        },
    )


def _window_statistic(statistic: str, column: str) -> str:
    """Helper column with a per-window or per-bin `statistic` of `column`."""
    return f"__ts_{statistic}__{column}"


def spectral_features(  # noqa: PLR0913
    expanded: Table,
    *,
    keys: Sequence[str],
    columns: Sequence[str],
    features: Sequence[SpectralFeature],
    window_size: int,
    sampling_frequency: float,
    naming: Naming,
) -> Table:
    """Spectral features of each expanded window, one row per `WINDOW_END`."""
    assert window_size >= 3
    window_keys = [*keys, WINDOW_END]

    # Least-squares line per window:
    # value ≈ mean + slope · (position_in_window - mean_position).
    mean_position = (window_size - 1) / 2
    position_variance = (window_size * window_size - 1) / 12
    # Window functions rather than an aggregate joined back, so the query
    # expands each window once.
    whole_window = ibis.window(group_by=window_keys)
    position_in_window = _integer(expanded, POSITION_IN_WINDOW)
    centred_position = position_in_window.cast(float) - mean_position

    def values(column: str) -> ir.FloatingColumn:
        return _floating(expanded, value_column(column))

    def residuals_of(column: str) -> ir.Value:
        mean = values(column).mean().over(whole_window)
        slope = (
            position_in_window.cov(values(column), how="pop").over(whole_window)
            / position_variance
        )
        return values(column) - (mean + slope * centred_position)

    # Per-window statistics the validity check reads after the spectrum.
    carried = {
        **{
            _window_statistic("non_null_count", column): values(column)
            .count()
            .over(whole_window)
            for column in columns
        },
        **{
            _window_statistic("scale", column): values(column)
            .abs()
            .max()
            .over(whole_window)
            for column in columns
        },
    }
    residuals = expanded.select(
        *window_keys,
        POSITION_IN_WINDOW,
        **carried,
        **{value_column(column): residuals_of(column) for column in columns},
    )

    # Real DFT of the residuals per frequency bin 0 .. window_size // 2.
    frequency_bins = ibis_ops.literal_table(
        f"__ts_bins_{window_size}",
        [(frequency_bin,) for frequency_bin in range(window_size // 2 + 1)],
        ibis.schema({FREQUENCY_BIN: "int64"}),
    )
    bin_rows = residuals.cross_join(frequency_bins)
    angle_factor = 2 * math.pi / window_size
    angle = (
        _integer(bin_rows, FREQUENCY_BIN) * _integer(bin_rows, POSITION_IN_WINDOW)
    ).cast(float) * angle_factor
    spectrum = bin_rows @ Aggregate(
        by=[*window_keys, FREQUENCY_BIN, *carried],
        expr={
            **{
                _window_statistic("real", column): (
                    _floating(bin_rows, value_column(column)) * angle.cos()
                ).sum()
                for column in columns
            },
            **{
                _window_statistic("imaginary", column): (
                    _floating(bin_rows, value_column(column)) * angle.sin()
                ).sum()
                for column in columns
            },
        },
    )
    spectrum = spectrum.mutate(
        **{
            FREQUENCY: _integer(spectrum, FREQUENCY_BIN).cast(float)
            * sampling_frequency
            / window_size
        },
        **{
            _window_statistic("magnitude", column): (
                _floating(spectrum, _window_statistic("real", column)) ** 2
                + _floating(spectrum, _window_statistic("imaginary", column)) ** 2
            ).sqrt()
            for column in columns
        },
    )
    cumulative = ibis.cumulative_window(
        group_by=window_keys, order_by=_integer(spectrum, FREQUENCY_BIN)
    )
    spectrum = spectrum.mutate(
        **{
            _window_statistic("cumulative_magnitude", column): _floating(
                spectrum, _window_statistic("magnitude", column)
            )
            .sum()
            .over(cumulative)
            for column in columns
        },
        **{
            _window_statistic("total_magnitude", column): _floating(
                spectrum, _window_statistic("magnitude", column)
            )
            .sum()
            .over(whole_window)
            for column in columns
        },
    )

    def view(column: str) -> Spectrum:
        return Spectrum(
            frequency_bin=_integer(spectrum, FREQUENCY_BIN),
            frequency=_floating(spectrum, FREQUENCY),
            magnitude=_floating(spectrum, _window_statistic("magnitude", column)),
            cumulative_magnitude=_floating(
                spectrum, _window_statistic("cumulative_magnitude", column)
            ),
            total_magnitude=_floating(
                spectrum, _window_statistic("total_magnitude", column)
            ),
            window_size=window_size,
        )

    def valid(column: str) -> ir.BooleanValue:
        """No null value, and more than rounding left after detrending."""
        non_null_count = _integer(spectrum, _window_statistic("non_null_count", column))
        scale = _floating(spectrum, _window_statistic("scale", column))
        total_magnitude = _floating(
            spectrum, _window_statistic("total_magnitude", column)
        )
        complete = non_null_count.max() == ibis.literal(window_size)
        not_zero = total_magnitude.max() > scale.max() * (ZERO_TOLERANCE * window_size)
        return complete & not_zero

    return spectrum @ Aggregate(
        by=window_keys,
        expr={
            naming(column, feature, window_size): _null_unless(
                valid(column), feature.reduce(view(column))
            )
            for column in columns
            for feature in features
        },
    )


def join_back(table: Table, results: Sequence[Table], *, keys: Sequence[str]) -> Table:
    """Left join each of `results` on each row's window end, in one flat join chain.

    `LeftJoin` would wrap each join in a selection of every column so far. Here
    the clashing key columns of each result get a reserved prefix instead.
    """
    joined = table
    for index, result in enumerate(results):
        joined = joined.left_join(
            result,
            [
                *(table[key] == result[key] for key in keys),
                _integer(table, POSITION) == _integer(result, WINDOW_END),
            ],
            rname=f"__ts_joined_{index}__{{name}}",
        )
    return joined
