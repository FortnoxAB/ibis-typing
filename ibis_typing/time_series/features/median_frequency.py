"""The `MedianFrequency` spectral feature."""

from __future__ import annotations

from attrs import frozen
from ibis import ir

from .base import SpectralFeature, Spectrum

__all__ = ["TIE_TOLERANCE", "MedianFrequency"]

# Margin above half the total magnitude. When the cumulative magnitude reaches
# exactly half at a bin, the result is the next, higher bin, independent of float
# rounding, unless the window varies by less than about 1e-6 of its level.
TIE_TOLERANCE = 1e-9


@frozen
class MedianFrequency(SpectralFeature):
    """Lowest frequency where the cumulative magnitude exceeds half the total.

    E.g. one cosine cycle over an 8-point window → `1 / 8` (times the sampling
    frequency). The window's least-squares line is removed first, so neither
    level nor trend dominates. With `window_size = 3` a non-null result is always
    `sampling_frequency / 3`.
    """

    @property
    def name(self) -> str:
        return "median_frequency"

    def reduce(self, spectrum: Spectrum) -> ir.Value:
        threshold = spectrum.total_magnitude * (0.5 + TIE_TOLERANCE)
        return spectrum.frequency.min(where=spectrum.cumulative_magnitude > threshold)
