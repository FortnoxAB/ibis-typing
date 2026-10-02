"""Trailing-window time series features for `ibis.Table` expressions."""

from __future__ import annotations

from collections.abc import Sequence

import ibis
from attrs import frozen
from ibis import Table

from .. import ibis_types as it
from ..ibis_extension_method import TableMethod
from . import stages
from .features import PointFeature, SpectralFeature, TimeSeriesFeature
from .validation import validate

__all__ = ["TimeSeriesFeatureExtraction"]


@frozen(kw_only=True)
class TimeSeriesFeatureExtraction(TableMethod):
    """Add features over the trailing `window_size` points of each row's series.

    A series is the rows sharing `keys`, ordered by `order_by`. Rows with fewer
    than `window_size` points get null. `sampling_frequency` scales the
    frequencies of spectral features. Columns prefixed `__ts_` are reserved.

    Not checked: keys are non-null, `(keys, order_by)` is unique and each series
    is evenly spaced without gaps. Nulls are never filled.
    """

    keys: Sequence[it.NameOrType]
    order_by: it.NameOrType
    columns: Sequence[it.NameOrType]
    features: Sequence[TimeSeriesFeature]
    windows: int | Sequence[int]
    window_unit: str | None = None
    sampling_frequency: float = 1.0

    @classmethod
    def rename_col(
        cls,
        col: it.NameOrType,
        feature: TimeSeriesFeature,
        *,
        window: int,
        window_unit: str | None = None,
    ) -> str:
        """Output column name.

        >>> from ibis_typing.time_series.features import Sum
        >>> TimeSeriesFeatureExtraction.rename_col("cash", Sum(), window=12)
        'cash__sum_last_12'
        >>> TimeSeriesFeatureExtraction.rename_col(
        ...     "cash", Sum(), window=12, window_unit="months"
        ... )
        'cash__sum_last_12_months'
        """
        unit = f"_{window_unit}" if window_unit else ""
        return f"{col}__{feature.name}_last_{window}{unit}"

    def output_name(
        self, column: it.NameOrType, feature: TimeSeriesFeature, window_size: int
    ) -> str:
        """Output column name of `feature` of `column` over `window_size` points.

        >>> from ibis_typing.time_series.features import Sum
        >>> TimeSeriesFeatureExtraction(
        ...     keys=["tenant"],
        ...     order_by="month",
        ...     columns=["cash"],
        ...     features=[Sum()],
        ...     windows=12,
        ...     window_unit="months",
        ... ).output_name("cash", Sum(), 12)
        'cash__sum_last_12_months'
        """
        return self.rename_col(
            column, feature, window=window_size, window_unit=self.window_unit
        )

    @property
    def window_sizes(self) -> tuple[int, ...]:
        return (self.windows,) if isinstance(self.windows, int) else tuple(self.windows)

    def apply(self, table: Table) -> Table:
        validate(self, table)
        keys = [str(key) for key in self.keys]
        columns = [str(column) for column in self.columns]
        point_features = [
            feature for feature in self.features if isinstance(feature, PointFeature)
        ]
        windowed = [feature for feature in point_features if feature.windowable]
        expanded_point = [
            feature for feature in point_features if not feature.windowable
        ]
        spectral = [
            feature for feature in self.features if isinstance(feature, SpectralFeature)
        ]

        result = stages.prepare(
            table,
            keys=keys,
            order_by=str(self.order_by),
            columns=columns,
            uses_lag=any(feature.uses_lag for feature in windowed),
        )
        for window_size in self.window_sizes:
            if windowed:
                result = result.mutate(
                    **stages.window_features(
                        result,
                        keys=keys,
                        columns=columns,
                        features=windowed,
                        window_size=window_size,
                        naming=self.output_name,
                    )
                )
            if expanded_point or spectral:
                result = self._apply_expanded(
                    result, keys, columns, expanded_point, spectral, window_size
                )

        helper_columns = [
            column for column in result.columns if column.startswith("__ts_")
        ]
        return result.drop(*helper_columns)

    def _apply_expanded(  # noqa: PLR0913
        self,
        table: Table,
        keys: list[str],
        columns: list[str],
        point_features: list[PointFeature],
        spectral_features: list[SpectralFeature],
        window_size: int,
    ) -> Table:
        expanded = stages.expand(
            table,
            keys=keys,
            columns=columns,
            window_size=window_size,
            uses_lag=any(feature.uses_lag for feature in point_features),
        )
        if point_features:
            result = stages.expanded_point_features(
                expanded,
                keys=keys,
                columns=columns,
                features=point_features,
                window_size=window_size,
                naming=self.output_name,
            )
            table = stages.join_back(table, result, keys=keys)
        if spectral_features and window_size < 3:
            # Detrending leaves nothing of a window with fewer than 3 points.
            nulls = {
                self.output_name(column, feature, window_size): ibis.null("float64")
                for column in columns
                for feature in spectral_features
            }
            table = table.mutate(**nulls)
        elif spectral_features:
            result = stages.spectral_features(
                expanded,
                keys=keys,
                columns=columns,
                features=spectral_features,
                window_size=window_size,
                sampling_frequency=self.sampling_frequency,
                naming=self.output_name,
            )
            table = stages.join_back(table, result, keys=keys)
        return table
