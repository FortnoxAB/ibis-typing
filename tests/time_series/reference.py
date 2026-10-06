"""Reference implementations to compare features with, and series to compare on.

The property tests in `features/` compare the SQL implementation of each feature
(window framing, incomplete windows, nulls, ordering, backend differences) with
an independent numpy or Python computation on random series. The hand-written
cases in each feature test define the expected semantics.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any

import numpy as np
import pytest
from hypothesis import strategies as st

MAX_WINDOW_SIZE = 12

# The same tolerances as the implementation, kept literal so the references stay
# independent of the package.
TIE_TOLERANCE = 1e-9
ZERO_TOLERANCE = 1e-12


def finite_series() -> st.SearchStrategy[list[float]]:
    """Bounded integer-valued floats, long enough for every window size."""
    return st.lists(
        st.integers(-1_000, 1_000).map(float), min_size=MAX_WINDOW_SIZE, max_size=30
    )


def window_sizes(min_size: int = 1) -> st.SearchStrategy[int]:
    return st.integers(min_size, MAX_WINDOW_SIZE)


def each_window(
    function: Callable[[list[float]], Any],
    values: Sequence[float],
    window_size: int = 3,
) -> list[Any]:
    """`function` of the trailing window ending at each value; None if incomplete."""
    return [
        function(list(values[end - window_size + 1 : end + 1]))
        if end >= window_size - 1
        else None
        for end in range(len(values))
    ]


def approx(expected: list[Any]) -> list[Any]:
    return [
        None if value is None else pytest.approx(value, rel=1e-6, abs=1e-6)
        for value in expected
    ]


def nunique(values: list[float]) -> int:
    return len(set(values))


def standard_deviation(values: list[float]) -> float | None:
    return float(np.std(values, ddof=1)) if len(values) > 1 else None


def mean_abs_diff(values: list[float]) -> float | None:
    return float(np.mean(np.abs(np.diff(values)))) if len(values) > 1 else None


def median_frequency_spectrum(
    values: list[float], sampling_frequency: float = 1.0
) -> tuple[np.ndarray, np.ndarray]:
    """Frequencies and magnitudes of the linearly detrended values."""
    points = np.asarray(values, dtype=float)
    positions = np.arange(len(points))
    slope, intercept = np.polyfit(positions, points, 1)
    residual = points - (intercept + slope * positions)
    frequency = np.fft.rfftfreq(len(points), 1 / sampling_frequency)
    return frequency, np.abs(np.fft.rfft(residual))


def median_frequency(
    values: list[float], sampling_frequency: float = 1.0
) -> float | None:
    if len(values) < 3:
        return None
    frequency, magnitude = median_frequency_spectrum(values, sampling_frequency)
    scale = max(abs(value) for value in values)
    if magnitude.sum() <= ZERO_TOLERANCE * len(values) * scale:
        return None
    threshold = (0.5 + TIE_TOLERANCE) * magnitude.sum()
    above = np.flatnonzero(np.cumsum(magnitude) > threshold)
    return float(frequency[above[0]])
