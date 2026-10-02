"""Query stages of `TimeSeriesFeatureExtraction`.

`prepare` numbers the rows of each series by `order_by` as `POSITION`; every later
stage orders by `POSITION`.
"""

from __future__ import annotations

import math
from collections.abc import Callable, Mapping, Sequence
from typing import cast

import ibis
from ibis import Table, ir

from .. import ibis_ops
from ..ibis_api import IfElse
from ..ibis_joins import InnerJoin, LeftJoin
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

# Below this magnitude relative to the window's scale, a detrended window is zero.
ZERO_TOLERANCE = 1e-9


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
    """Add each row's `POSITION` in its series and, if `uses_lag`, previous values."""
    series = ibis.window(group_by=list(keys), order_by=table[order_by])
    previous_values = {
        previous_values_column(column): _floating(table, column).lag().over(series)
        for column in columns
        if uses_lag
    }
    return table.mutate(**{POSITION: ibis.row_number().over(series)}, **previous_values)


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
        values = _floating(table, column)
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
    """One row per point of each complete window, ending at `WINDOW_END`."""
    position = _integer(table, POSITION)
    window_ends = table.filter(position >= ibis.literal(window_size - 1)).select(
        *keys, **{WINDOW_END: position}
    )
    series_points = table.select(*keys, POSITION, *columns)
    point_position = _integer(series_points, POSITION)
    window_end = _integer(window_ends, WINDOW_END)
    joined = window_ends.join(
        series_points,
        [
            *keys,
            point_position > window_end - window_size,
            point_position <= window_end,
        ],
    )
    position_in_window = (
        _integer(joined, POSITION) - _integer(joined, WINDOW_END) + (window_size - 1)
    )
    expanded = joined.select(
        *keys,
        WINDOW_END,
        **{POSITION_IN_WINDOW: position_in_window},
        **{column: _floating(joined, column) for column in columns},
    )
    if not uses_lag:
        return expanded
    window = ibis.window(
        group_by=[*keys, WINDOW_END], order_by=_integer(expanded, POSITION_IN_WINDOW)
    )
    return expanded.mutate(
        **{
            previous_values_column(column): _floating(expanded, column)
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
            values=_floating(expanded, column),
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


def _non_null_count(column: str) -> str:
    """Helper column with the number of non-null values of `column` per window."""
    return f"__ts_non_null_count__{column}"


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

    def mean(column: str) -> str:
        return _window_statistic("mean", column)

    def slope(column: str) -> str:
        return _window_statistic("slope", column)

    def scale(column: str) -> str:
        return _window_statistic("scale", column)

    def real(column: str) -> str:
        return _window_statistic("real", column)

    def imaginary(column: str) -> str:
        return _window_statistic("imaginary", column)

    def magnitude(column: str) -> str:
        return _window_statistic("magnitude", column)

    def cumulative_magnitude(column: str) -> str:
        return _window_statistic("cumulative_magnitude", column)

    def total_magnitude(column: str) -> str:
        return _window_statistic("total_magnitude", column)

    # Least-squares line per window:
    # value ≈ mean + slope · (position_in_window - mean_position).
    mean_position = (window_size - 1) / 2
    position_variance = (window_size * window_size - 1) / 12
    position_in_window = _integer(expanded, POSITION_IN_WINDOW)
    window_statistics = expanded @ Aggregate(
        by=window_keys,
        expr={
            **{
                _non_null_count(column): _floating(expanded, column).count()
                for column in columns
            },
            **{
                scale(column): _floating(expanded, column).abs().max()
                for column in columns
            },
            **{mean(column): _floating(expanded, column).mean() for column in columns},
            **{
                slope(column): position_in_window.cov(
                    _floating(expanded, column), how="pop"
                )
                / position_variance
                for column in columns
            },
        },
    )
    joined = expanded @ InnerJoin(window_statistics, keys=window_keys)
    centred_position = _integer(joined, POSITION_IN_WINDOW).cast(float) - mean_position
    residuals = joined.select(
        *window_keys,
        POSITION_IN_WINDOW,
        **{
            column: _floating(joined, column)
            - (
                _floating(joined, mean(column))
                + _floating(joined, slope(column)) * centred_position
            )
            for column in columns
        },
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
        by=[*window_keys, FREQUENCY_BIN],
        expr={
            **{
                real(column): (_floating(bin_rows, column) * angle.cos()).sum()
                for column in columns
            },
            **{
                imaginary(column): (_floating(bin_rows, column) * angle.sin()).sum()
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
            magnitude(column): (
                _floating(spectrum, real(column)) ** 2
                + _floating(spectrum, imaginary(column)) ** 2
            ).sqrt()
            for column in columns
        },
    )
    cumulative = ibis.cumulative_window(
        group_by=window_keys, order_by=_integer(spectrum, FREQUENCY_BIN)
    )
    whole_window = ibis.window(group_by=window_keys)
    spectrum = spectrum.mutate(
        **{
            cumulative_magnitude(column): _floating(spectrum, magnitude(column))
            .sum()
            .over(cumulative)
            for column in columns
        },
        **{
            total_magnitude(column): _floating(spectrum, magnitude(column))
            .sum()
            .over(whole_window)
            for column in columns
        },
    )

    def view(column: str) -> Spectrum:
        return Spectrum(
            frequency_bin=_integer(spectrum, FREQUENCY_BIN),
            frequency=_floating(spectrum, FREQUENCY),
            magnitude=_floating(spectrum, magnitude(column)),
            cumulative_magnitude=_floating(spectrum, cumulative_magnitude(column)),
            total_magnitude=_floating(spectrum, total_magnitude(column)),
            window_size=window_size,
        )

    output_names = {
        (column, feature): naming(column, feature, window_size)
        for column in columns
        for feature in features
    }
    reduced = spectrum @ Aggregate(
        by=window_keys,
        expr={
            **{
                name: feature.reduce(view(column))
                for (column, feature), name in output_names.items()
            },
            **{
                total_magnitude(column): _floating(
                    spectrum, total_magnitude(column)
                ).max()
                for column in columns
            },
        },
    )
    result = reduced @ InnerJoin(window_statistics, keys=window_keys)

    # Null for windows with a null value or a zero residual.
    def valid(column: str) -> ir.BooleanValue:
        not_zero = _floating(result, total_magnitude(column)) > _floating(
            result, scale(column)
        ) * (ZERO_TOLERANCE * window_size)
        complete = _integer(result, _non_null_count(column)) == ibis.literal(
            window_size
        )
        return complete & not_zero

    return result.select(
        *window_keys,
        **{
            name: _null_unless(valid(column), result[name])
            for (column, _), name in output_names.items()
        },
    )


def join_back(table: Table, result: Table, *, keys: Sequence[str]) -> Table:
    """Left join `result` on each row's window end and add its new columns."""
    window_results = result.rename({POSITION: WINDOW_END})
    return table @ LeftJoin(window_results, keys=[*keys, POSITION])
