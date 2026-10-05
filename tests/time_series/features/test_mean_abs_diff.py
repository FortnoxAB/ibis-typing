from __future__ import annotations

import pytest
from hypothesis import given

from ibis_typing.time_series.features import MeanAbsDiff
from tests.time_series.reference import (
    approx,
    each_window,
    finite_series,
    mean_abs_diff,
    window_sizes,
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
