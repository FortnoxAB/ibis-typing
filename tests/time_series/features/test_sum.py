from __future__ import annotations

import numpy as np
import pytest
from hypothesis import given

from ibis_typing.time_series.features import Sum
from tests.time_series.reference import approx, each_window, finite_series, window_sizes


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
