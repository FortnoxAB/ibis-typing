from __future__ import annotations

import pytest
from hypothesis import given

from ibis_typing.time_series.features import Min
from tests.time_series.reference import approx, each_window, finite_series, window_sizes


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
