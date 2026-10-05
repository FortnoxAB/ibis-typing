from __future__ import annotations

import pytest
from hypothesis import given

from ibis_typing.time_series.features import NUnique
from tests.time_series.reference import (
    each_window,
    finite_series,
    nunique,
    window_sizes,
)


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
