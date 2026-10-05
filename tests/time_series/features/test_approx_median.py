from __future__ import annotations

import pytest
from hypothesis import given

from ibis_typing.time_series.features import ApproxMedian
from tests.time_series.reference import each_window, finite_series, window_sizes


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
