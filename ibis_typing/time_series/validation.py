"""Argument checks of `TimeSeriesFeatureExtraction` against its input table."""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

from .features import PointFeature, SpectralFeature

if TYPE_CHECKING:
    from ibis import Table

    from .extraction import TimeSeriesFeatureExtraction

__all__ = ["validate"]


def validate(extraction: TimeSeriesFeatureExtraction, table: Table) -> None:
    """Raise if `extraction` cannot be applied to `table`, checking in this order."""
    _has_columns_features_and_windows(extraction)
    _window_sizes_are_ints(extraction)
    _window_sizes_are_at_least_one(extraction)
    _sampling_frequency_is_positive_and_finite(extraction)
    _features_are_point_or_spectral(extraction)
    _columns_exist(extraction, table)
    _no_reserved_prefix(table)
    _columns_are_numeric(extraction, table)
    _no_key_is_a_value_column(extraction)
    _order_by_is_not_a_key(extraction)
    output_names = _output_names(extraction)
    _output_names_are_unique(output_names)
    _output_names_are_new(output_names, table)


def _has_columns_features_and_windows(extraction: TimeSeriesFeatureExtraction) -> None:
    if not extraction.columns:
        raise ValueError("TimeSeriesFeatureExtraction needs at least one column.")
    if not extraction.features:
        raise ValueError("TimeSeriesFeatureExtraction needs at least one feature.")
    if not extraction.window_sizes:
        raise ValueError("TimeSeriesFeatureExtraction needs at least one window.")


def _window_sizes_are_ints(extraction: TimeSeriesFeatureExtraction) -> None:
    invalid = [
        size
        for size in extraction.window_sizes
        if isinstance(size, bool) or not isinstance(size, int)
    ]
    if invalid:
        raise TypeError(f"Window sizes must be ints, got: {invalid}")


def _window_sizes_are_at_least_one(extraction: TimeSeriesFeatureExtraction) -> None:
    invalid = [size for size in extraction.window_sizes if size < 1]
    if invalid:
        raise ValueError(f"Window sizes must be at least 1, got: {invalid}")


def _sampling_frequency_is_positive_and_finite(
    extraction: TimeSeriesFeatureExtraction,
) -> None:
    frequency = extraction.sampling_frequency
    if not math.isfinite(frequency) or frequency <= 0:
        raise ValueError(
            f"sampling_frequency must be positive and finite, got: {frequency}"
        )


def _features_are_point_or_spectral(extraction: TimeSeriesFeatureExtraction) -> None:
    unknown = [
        feature
        for feature in extraction.features
        if not isinstance(feature, PointFeature | SpectralFeature)
    ]
    if unknown:
        raise TypeError(
            f"Features must be a PointFeature or SpectralFeature, got: {unknown}"
        )


def _columns_exist(extraction: TimeSeriesFeatureExtraction, table: Table) -> None:
    required = [*extraction.keys, extraction.order_by, *extraction.columns]
    missing = [column for column in required if column not in table.columns]
    if missing:
        raise ValueError(f"Columns not in table: {missing}")


def _no_reserved_prefix(table: Table) -> None:
    reserved = [column for column in table.columns if column.startswith("__ts_")]
    if reserved:
        raise ValueError(f"Columns use the reserved prefix '__ts_': {reserved}")


def _columns_are_numeric(extraction: TimeSeriesFeatureExtraction, table: Table) -> None:
    non_numeric = [
        column for column in extraction.columns if not table[column].type().is_numeric()
    ]
    if non_numeric:
        raise ValueError(f"Columns must be numeric: {non_numeric}")


def _no_key_is_a_value_column(extraction: TimeSeriesFeatureExtraction) -> None:
    keys = {str(key) for key in extraction.keys}
    overlap = [str(column) for column in extraction.columns if str(column) in keys]
    if overlap:
        raise ValueError(f"Columns cannot be both a key and a value column: {overlap}")


def _order_by_is_not_a_key(extraction: TimeSeriesFeatureExtraction) -> None:
    if str(extraction.order_by) in {str(key) for key in extraction.keys}:
        raise ValueError(f"order_by cannot also be a key: {extraction.order_by}")


def _output_names(extraction: TimeSeriesFeatureExtraction) -> list[str]:
    return [
        extraction.output_name(column, feature, size)
        for size in extraction.window_sizes
        for column in extraction.columns
        for feature in extraction.features
    ]


def _output_names_are_unique(output_names: list[str]) -> None:
    duplicates = sorted({name for name in output_names if output_names.count(name) > 1})
    if duplicates:
        raise ValueError(f"Duplicate output columns: {duplicates}")


def _output_names_are_new(output_names: list[str], table: Table) -> None:
    existing = [name for name in output_names if name in table.columns]
    if existing:
        raise ValueError(f"Output columns already exist in table: {existing}")
