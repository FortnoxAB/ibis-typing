from __future__ import annotations

import pytest

from ibis_typing.time_series.features import Count


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
