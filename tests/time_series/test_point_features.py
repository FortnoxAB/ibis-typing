from __future__ import annotations

import math

import numpy as np
import pytest
from hypothesis import given

from ibis_typing.time_series.features import (
    ApproxMedian,
    Count,
    Max,
    Mean,
    MeanAbsDiff,
    Min,
    NUnique,
    StandardDeviation,
    Sum,
)
from tests.time_series.reference import (
    approx,
    each_window,
    finite_series,
    mean_abs_diff,
    nunique,
    standard_deviation,
    window_sizes,
)


@pytest.mark.parametrize(
    ("values", "expected"),
    [
        ([1.0, 2.0, 4.0, 8.0], [None, None, 7.0, 14.0]),
        ([1.0, None, 4.0], [None, None, 5.0]),
        ([None, None, None], [None, None, None]),
        ([0.0, 1.0], [None, None]),
        ([1.0], [None]),
    ],
)
def test_sum_of_the_trailing_window(trailing, values, expected):
    assert trailing(values, Sum(), window_size=3) == expected


@given(values=finite_series(), window_size=window_sizes())
def test_sum_matches_numpy(trailing, values, window_size):
    assert trailing(values, Sum(), window_size=window_size) == approx(
        each_window(np.sum, values, window_size)
    )


@pytest.mark.parametrize(
    ("values", "expected"),
    [
        ([1.0, 2.0, 6.0, 7.0], [None, None, 3.0, 5.0]),
        ([1.0, None, 4.0], [None, None, 2.5]),
        ([None, None, None], [None, None, None]),
        ([0.0, 1.0], [None, None]),
        ([1.0], [None]),
    ],
)
def test_mean_of_the_trailing_window(trailing, values, expected):
    assert trailing(values, Mean(), window_size=3) == expected


@given(values=finite_series(), window_size=window_sizes())
def test_mean_matches_numpy(trailing, values, window_size):
    assert trailing(values, Mean(), window_size=window_size) == approx(
        each_window(np.mean, values, window_size)
    )


@pytest.mark.parametrize(
    ("values", "expected"),
    [
        ([3.0, 1.0, 2.0, 5.0], [None, None, 1.0, 1.0]),
        # Rows before the window are forgotten.
        ([0.0, 4.0, 5.0, 6.0], [None, None, 0.0, 4.0]),
        ([3.0, None, 4.0], [None, None, 3.0]),
        ([None, None, None], [None, None, None]),
        ([0.0, 1.0], [None, None]),
        ([1.0], [None]),
    ],
)
def test_min_of_the_trailing_window(trailing, values, expected):
    assert trailing(values, Min(), window_size=3) == expected


@given(values=finite_series(), window_size=window_sizes())
def test_min_matches_the_builtin(trailing, values, window_size):
    assert trailing(values, Min(), window_size=window_size) == approx(
        each_window(min, values, window_size)
    )


@pytest.mark.parametrize(
    ("values", "expected"),
    [
        ([3.0, 1.0, 2.0, 0.0], [None, None, 3.0, 2.0]),
        ([3.0, None, 4.0], [None, None, 4.0]),
        ([None, None, None], [None, None, None]),
        ([0.0, 1.0], [None, None]),
        ([1.0], [None]),
    ],
)
def test_max_of_the_trailing_window(trailing, values, expected):
    assert trailing(values, Max(), window_size=3) == expected


@given(values=finite_series(), window_size=window_sizes())
def test_max_matches_the_builtin(trailing, values, window_size):
    assert trailing(values, Max(), window_size=window_size) == approx(
        each_window(max, values, window_size)
    )


@pytest.mark.parametrize(
    ("values", "expected"),
    [
        ([1.0, 2.0, 4.0, 8.0], [None, None, 3, 3]),
        ([1.0, None, 4.0], [None, None, 2]),
        ([None, None, None], [None, None, 0]),
        ([0.0, 1.0], [None, None]),
        ([1.0], [None]),
    ],
)
def test_count_of_the_trailing_window(trailing, values, expected):
    assert trailing(values, Count(), window_size=3) == expected


@pytest.mark.parametrize(
    ("values", "expected"),
    [
        ([1.0, 2.0, 2.0, 2.0], [None, None, 2, 1]),
        ([1.0, None, 1.0], [None, None, 1]),
        ([None, None, None], [None, None, 0]),
        ([0.0, 1.0], [None, None]),
        ([1.0], [None]),
    ],
)
def test_nunique_of_the_trailing_window(trailing, values, expected):
    assert trailing(values, NUnique(), window_size=3) == expected


@given(values=finite_series(), window_size=window_sizes())
def test_nunique_matches_the_reference(trailing, values, window_size):
    assert trailing(values, NUnique(), window_size=window_size) == each_window(
        nunique, values, window_size
    )


@pytest.mark.parametrize(
    ("values", "expected"),
    [
        ([1.0, 9.0, 5.0, 5.0], [None, None, 5.0, 5.0]),
        ([None, None, None], [None, None, None]),
        ([0.0, 1.0], [None, None]),
        ([1.0], [None]),
    ],
)
def test_approx_median_of_the_trailing_window(trailing, values, expected):
    assert trailing(values, ApproxMedian(), window_size=3) == expected


@given(values=finite_series(), window_size=window_sizes())
def test_approx_median_lies_within_the_window(trailing, values, window_size):
    medians = trailing(values, ApproxMedian(), window_size=window_size)
    windows = each_window(list, values, window_size)
    for median, window in zip(medians, windows, strict=True):
        if window is None:
            assert median is None
        else:
            assert min(window) <= median <= max(window)


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


@pytest.mark.parametrize(
    ("values", "window_size", "expected"),
    [
        ([1.0, 2.0, 4.0, 1.0], 3, [None, None, 1.5, 2.5]),
        ([100.0, 1.0, 1.0, 1.0], 3, [None, None, 49.5, 0.0]),
        ([3.0, 3.0, 3.0], 3, [None, None, 0.0]),
        # A single-row window has no steps, so it is null.
        ([1.0, 5.0], 1, [None, None]),
        ([1.0, None, 4.0, 6.0], 3, [None, None, None, 2.0]),
        ([0.0, 1.0], 3, [None, None]),
        ([1.0], 3, [None]),
    ],
)
def test_mean_abs_diff_of_the_trailing_window(trailing, values, window_size, expected):
    assert trailing(values, MeanAbsDiff(), window_size=window_size) == expected


@given(values=finite_series(), window_size=window_sizes())
def test_mean_abs_diff_matches_the_reference(trailing, values, window_size):
    assert trailing(values, MeanAbsDiff(), window_size=window_size) == approx(
        each_window(mean_abs_diff, values, window_size)
    )
