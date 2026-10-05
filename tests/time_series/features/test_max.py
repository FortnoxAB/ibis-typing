from __future__ import annotations

import pytest
from hypothesis import given

from ibis_typing.time_series.features import Max
from tests.time_series.reference import approx, each_window, finite_series, window_sizes


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
