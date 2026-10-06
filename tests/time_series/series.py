"""Test helpers: a tiny series schema and an extraction over it."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import Any

import ibis
from attrs import frozen

from ibis_typing import IbisSchema, it
from ibis_typing.time_series import TimeSeriesFeatureExtraction
from ibis_typing.time_series.features import TimeSeriesFeature

type Value = float | None


@frozen
class Point(IbisSchema):
    key: it.String = None
    time: it.Int64 = None
    value: it.Float64 = None


def series(values: Sequence[Value], *, key: str = "a") -> list[Point]:
    """One series: `values[i]` at `time = i`."""
    return [Point(key=key, time=time, value=value) for time, value in enumerate(values)]


def table(values: Sequence[Value] = (1.0, 2.0)) -> ibis.Table:
    return Point.of_rows(series(values)).table


def extraction(
    *features: TimeSeriesFeature, **overrides: Any
) -> TimeSeriesFeatureExtraction:
    """An extraction of `value`, with a series per `key` ordered by `time`."""
    arguments: dict[str, Any] = {
        "keys": ("key",),
        "order_by": "time",
        "columns": ("value",),
        "features": features,
        "windows": 2,
    }
    return TimeSeriesFeatureExtraction(**{**arguments, **overrides})


def oldest_first(rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(rows, key=lambda row: row["time"])
