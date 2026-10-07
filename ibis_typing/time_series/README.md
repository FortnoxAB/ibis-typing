# `ibis_typing.time_series` — Time Series Features

Adds trailing-window features to every row of an `ibis.Table` with
`table @ TimeSeriesFeatureExtraction(...)`, a
[`TableMethod`](../ibis_extension_method.py). Runs on DuckDB and Trino.

---

## Series, windows and names

- A **series** is the rows sharing `keys`, ordered by `order_by`. `keys`, `order_by`
  and `columns` take column names or `IbisSchema.cols` fields.
- A **window** of size `n` is the `n` points of a series ending at, and including, a
  row. Rows with fewer than `n` points get null.
- `windows` lists the window sizes. Each size adds its own columns.
- Every row and input column is kept. Each value column in `columns` gets one new
  column per feature and window size, named
  `{column}__{feature.name}_last_{window_size}` or, with `window_unit`,
  `{column}__{feature.name}_last_{window_size}_{window_unit}`.
- `sampling_frequency` (default `1.0`) scales the frequencies of spectral features.

```python
from datetime import date

from attrs import frozen

from ibis_typing import IbisSchema, it
from ibis_typing.time_series import TimeSeriesFeatureExtraction
from ibis_typing.time_series.features import MedianFrequency, StandardDeviation, Sum


@frozen
class Balance(IbisSchema):
    tenant: it.String = None
    month: it.Date = None
    cash: it.Float64 = None


balances = Balance.of_rows(
    [
        Balance(tenant="a", month=date(2024, month, 1), cash=float(month % 3))
        for month in range(1, 13)
    ]
)
cols = Balance.cols

table = balances.table @ TimeSeriesFeatureExtraction(
    keys=[cols.tenant],
    order_by=cols.month,
    columns=[cols.cash],
    features=[Sum(), StandardDeviation(), MedianFrequency()],
    windows=[6, 12],
    window_unit="months",
)
# Adds cash__{sum,standard_deviation,median_frequency}_last_{6,12}_months.
# December: sums 6.0 and 12.0, standard deviations 0.894… and 0.852…,
# median frequency 1/3 for both windows.
```

`TimeSeriesFeatureExtraction.rename_col(col, feature, window=..., window_unit=...)`
and the instance method `output_name(column, feature, window_size)` return the name
of an output column.

## Input contract

Checked when the method is applied, in this order, raising `ValueError` unless noted:

- At least one column, feature and window.
- Window sizes are ints (`TypeError`; a `bool` is not) and at least 1.
- `sampling_frequency` is positive and finite.
- Features are `PointFeature` or `SpectralFeature` instances (`TypeError`).
- `keys`, `order_by` and `columns` exist.
- No input column uses the reserved prefix `__ts_`.
- `columns` are numeric.
- `keys` and `columns` are disjoint, and `order_by` is not a key.
- Output columns are unique and do not already exist.

Not checked, and up to the caller:

- Keys are non-null.
- `(keys, order_by)` is unique.
- Each series is evenly spaced, without gaps. A window counts points, not time.

Nulls are never filled. Point features skip null values; spectral features are null
for windows that contain one.

Values are cast to `float64` first, so integer columns cannot overflow, and every
built-in feature but `Count` and `NUnique` is a float, e.g. `Sum` of an `int64`.

## Built-in features

All in `ibis_typing.time_series.features`.

| Feature             | Value per window                                                        |
|---------------------|-------------------------------------------------------------------------|
| `Sum`               | Sum of the non-null values                                              |
| `Mean`              | Mean of the non-null values                                             |
| `Min`               | Smallest non-null value                                                 |
| `Max`               | Largest non-null value                                                  |
| `Count`             | Number of non-null values                                               |
| `NUnique`           | Number of distinct non-null values                                      |
| `ApproxMedian`      | Approximate median of the non-null values                               |
| `StandardDeviation` | Sample standard deviation; null with fewer than two non-null values     |
| `MeanAbsDiff`       | Mean absolute step between consecutive values                           |
| `MedianFrequency`   | Lowest frequency where the cumulative magnitude exceeds half the total |

`MeanAbsDiff` skips steps touching a null and is null for a one-point window.
`NUnique` sets `windowable = False` (see below).

`MedianFrequency` is a spectral feature, computed on the linearly detrended window,
so neither level nor trend dominates. It is null for windows with a null value, fewer
than 3 points or nothing left after detrending, and scales with `sampling_frequency`.

## Adding a feature

Subclass `PointFeature` or `SpectralFeature` with `@frozen` and define `reduce`, which
returns one ibis aggregate. The output column suffix, `name`, defaults to the
snake_case class name (`MeanStep` → `mean_step`); override the `name` property to
change it or to include parameters.

### Point features

`reduce(self, points)` gets the window's points as columns (`Points`):

- `points.values` — the value column.
- `points.window_size` — the window size.
- `points.previous_values` — the previous point's value, null for the window's oldest
  point. Requires `uses_lag = True`.
- `points.position` (0 for the oldest point) and `points.steps_from_newest` (0 for the
  newest point). Require `windowable = False`.

By default a point feature runs as a SQL window function. With `windowable = False`,
each window is expanded into rows and grouped, which costs more. A window function
with `uses_lag = True` is null for a window size of 1. Reading an attribute without
its flag raises a `TypeError` naming the flag.

```python
from typing import ClassVar

from attrs import frozen
from ibis import ir

from ibis_typing.time_series.features import PointFeature, Points


@frozen
class Range(PointFeature):
    def reduce(self, points: Points) -> ir.Value:
        return points.values.max() - points.values.min()


@frozen
class MeanStep(PointFeature):
    uses_lag: ClassVar[bool] = True

    def reduce(self, points: Points) -> ir.Value:
        return (points.values - points.previous_values).mean()


@frozen
class RecencyWeightedMean(PointFeature):
    windowable: ClassVar[bool] = False

    def reduce(self, points: Points) -> ir.Value:
        weight = points.position + 1
        return (points.values * weight).sum() / weight.sum()
```

### Spectral features

`reduce(self, spectrum)` gets one row per frequency bin of the window's real DFT
(`Spectrum`), after its least-squares line is removed:

- `spectrum.frequency_bin` — `0 .. window_size // 2`.
- `spectrum.frequency` — `frequency_bin * sampling_frequency / window_size`.
- `spectrum.magnitude` — the bin's magnitude.
- `spectrum.cumulative_magnitude` — `magnitude` summed up to and including the bin.
- `spectrum.total_magnitude` — `magnitude` summed over all bins.
- `spectrum.window_size` — the window size.

Windows with a null value, fewer than 3 points or nothing left after detrending are
null. The cost of spectral features grows with the square of the window size, so they
are meant for small windows of tens of points, e.g. 12 or 24.

```python
from attrs import frozen
from ibis import ir

from ibis_typing.time_series.features import SpectralFeature, Spectrum


@frozen
class PeakMagnitude(SpectralFeature):
    def reduce(self, spectrum: Spectrum) -> ir.Value:
        return spectrum.magnitude.max()
```
