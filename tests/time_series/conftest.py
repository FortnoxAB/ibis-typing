from __future__ import annotations

import random
from collections.abc import Callable, Sequence
from typing import Any

import pytest

from ibis_typing.fixtures.expressions import EvaluateExpr
from ibis_typing.time_series import TimeSeriesFeatureExtraction
from ibis_typing.time_series.features import TimeSeriesFeature
from tests.time_series.series import Point, Value, extraction, oldest_first, series


@pytest.fixture
def trailing(evaluate_expr: EvaluateExpr) -> Callable[..., list[Any]]:
    def run(
        values: Sequence[Value],
        feature: TimeSeriesFeature,
        *,
        window_size: int,
        sampling_frequency: float = 1.0,
    ) -> list[Any]:
        """`feature` over the trailing `window_size` values of each row, oldest first.

        The rows are shuffled first, their order never matters.
        """
        points = series(values)
        random.Random(0).shuffle(points)
        method = extraction(
            feature, windows=[window_size], sampling_frequency=sampling_frequency
        )
        output = TimeSeriesFeatureExtraction.rename_col(
            "value", feature, window=window_size
        )
        rows = evaluate_expr(Point.of_rows(points).table @ method)
        return [row[output] for row in oldest_first(rows)]

    return run
