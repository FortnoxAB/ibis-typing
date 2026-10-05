from __future__ import annotations

import math

import pytest
from hypothesis import given

from ibis_typing.time_series.features import StandardDeviation
from tests.time_series.reference import (
    approx,
    each_window,
    finite_series,
    standard_deviation,
    window_sizes,
)


@pytest.mark.parametrize(
    ("values", "window_size", "expected"),
    [
        ([1.0, 2.0, 3.0, 3.0], 3, [None, None, 1.0, math.sqrt(1 / 3)]),
        ([4.0, 4.0, 4.0], 3, [None, None, 0.0]),
        # The sample standard deviation needs at least two values.
        ([4.0, 7.0], 1, [None, None]),
        # Nulls are skipped: the deviation of [1, 3].
        ([1.0, None, 3.0], 3, [None, None, math.sqrt(2)]),
        ([None, 5.0, None], 3, [None, None, None]),
        ([None, None, None], 3, [None, None, None]),
        ([0.0, 1.0], 3, [None, None]),
        ([1.0], 3, [None]),
    ],
)
def test_standard_deviation_of_the_trailing_window(
    trailing, values, window_size, expected
):
    actual = trailing(values, StandardDeviation(), window_size=window_size)
    assert actual == approx(expected)


@given(values=finite_series(), window_size=window_sizes())
def test_standard_deviation_matches_the_reference(trailing, values, window_size):
    assert trailing(values, StandardDeviation(), window_size=window_size) == approx(
        each_window(standard_deviation, values, window_size)
    )
