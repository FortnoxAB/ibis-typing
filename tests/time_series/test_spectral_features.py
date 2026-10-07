from __future__ import annotations

import math

import pytest
from hypothesis import given

from ibis_typing.time_series.features import MedianFrequency
from tests.time_series.reference import (
    approx,
    each_window,
    finite_series,
    median_frequency,
    window_sizes,
)


def wave(cycles: int, window_size: int) -> list[float]:
    return [
        math.cos(2 * math.pi * cycles * position / window_size)
        for position in range(window_size)
    ]


@pytest.mark.parametrize(
    ("values", "window_size", "expected"),
    [
        # A slow wave has a low frequency.
        (wave(1, 8), 8, [None] * 7 + [1 / 8]),
        # An alternating series has the highest frequency.
        (wave(4, 8), 8, [None] * 7 + [0.5]),
        # The level is ignored.
        ([value + 1_000 for value in wave(1, 8)], 8, [None] * 7 + [1 / 8]),
        # Equal bins resolve to the higher frequency.
        ([-2.0, -5.0, -4.0, 1.0, 0.0], 5, [None] * 4 + [0.4]),
        # A small variation on a large level still has a frequency.
        (
            [10_000_000.0 + 0.01 * (position % 2) for position in range(4)],
            4,
            [None] * 3 + [0.5],
        ),
        # Nothing is left after removing the trend line, so these are null.
        ([5.0] * 4, 3, [None] * 4),
        ([1.0, 2.0, 3.0, 4.0], 3, [None] * 4),
        ([0.0] * 4, 3, [None] * 4),
        ([10_000_000.0] * 4, 3, [None] * 4),
        ([1e6 + 2.0 * position for position in range(6)], 4, [None] * 6),
        # A window below three rows is null.
        ([1.0, 5.0, 2.0], 2, [None] * 3),
        # A window with a null is null.
        ([1.0, None, 3.0, 0.0, 2.0], 4, [None] * 5),
        ([0.0, 1.0], 3, [None, None]),
        ([1.0], 3, [None]),
    ],
)
def test_median_frequency_of_the_trailing_window(
    trailing, values, window_size, expected
):
    actual = trailing(values, MedianFrequency(), window_size=window_size)
    assert actual == approx(expected)


@pytest.mark.parametrize("trend", [0.0, 5.0, -250.0])
def test_a_linear_trend_does_not_change_the_median_frequency(trailing, trend):
    values = [value + trend * position for position, value in enumerate(wave(2, 12))]
    actual = trailing(values, MedianFrequency(), window_size=12)
    assert actual[-1] == pytest.approx(2 / 12)


@given(values=finite_series(), window_size=window_sizes(min_size=3))
def test_median_frequency_matches_the_reference(trailing, values, window_size):
    assert trailing(values, MedianFrequency(), window_size=window_size) == approx(
        each_window(median_frequency, values, window_size)
    )
