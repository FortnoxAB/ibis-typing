from __future__ import annotations

from datetime import date

from attrs import frozen

from ibis_typing import Expression, IbisSchema, IbisTable, it
from ibis_typing.time_series import TimeSeriesFeatureExtraction
from ibis_typing.time_series.features import MeanAbsDiff, MedianFrequency, NUnique, Sum

JANUARY, FEBRUARY, MARCH, APRIL = (date(2024, month, 1) for month in range(1, 5))


@frozen
class Balance(IbisSchema):
    tenant: it.Int64 = None
    month: it.Date = None
    monetary_amount: it.Float64 = None
    # Neither key, order nor value column: carried through unchanged.
    currency: it.String = None


@frozen
class CashFeatures(Balance, Expression):
    cash__sum_last_2_months: it.Float64 = None
    cash__mean_abs_diff_last_2_months: it.Float64 = None

    @classmethod
    def from_expression(cls, inputs: IbisTable[Balance]):
        cols = inputs.cols
        table = inputs.table @ TimeSeriesFeatureExtraction(
            keys=[cols.tenant],
            order_by=cols.month,
            columns=[cols.monetary_amount],
            features=[Sum(), MeanAbsDiff()],
            windows=[2],
            window_unit="months",
        )
        return cls.of(table)


@frozen
class CashFeaturesOverTwoWindows(Balance, Expression):
    cash__sum_last_2: it.Float64 = None
    cash__mean_abs_diff_last_2: it.Float64 = None
    cash__sum_last_3: it.Float64 = None
    cash__mean_abs_diff_last_3: it.Float64 = None

    @classmethod
    def from_expression(cls, inputs: IbisTable[Balance]):
        cols = inputs.cols
        table = inputs.table @ TimeSeriesFeatureExtraction(
            keys=[cols.tenant],
            order_by=cols.month,
            columns=[cols.monetary_amount],
            features=[Sum(), MeanAbsDiff()],
            windows=(2, 3),
        )
        return cls.of(table)


@frozen
class CashAndDebt(IbisSchema):
    tenant: it.Int64 = None
    month: it.Date = None
    cash: it.Float64 = None
    debt: it.Float64 = None


@frozen
class CashAndDebtFeatures(CashAndDebt, Expression):
    cash__sum_last_2: it.Float64 = None
    cash__mean_abs_diff_last_2: it.Float64 = None
    debt__sum_last_2: it.Float64 = None
    debt__mean_abs_diff_last_2: it.Float64 = None
    cash__sum_last_3: it.Float64 = None
    cash__mean_abs_diff_last_3: it.Float64 = None
    debt__sum_last_3: it.Float64 = None
    debt__mean_abs_diff_last_3: it.Float64 = None

    @classmethod
    def from_expression(cls, inputs: IbisTable[CashAndDebt]):
        cols = inputs.cols
        table = inputs.table @ TimeSeriesFeatureExtraction(
            keys=[cols.tenant],
            order_by=cols.month,
            columns=[cols.cash, cols.debt],
            features=[Sum(), MeanAbsDiff()],
            windows=(2, 3),
        )
        return cls.of(table)


@frozen
class WholeUnitBalance(IbisSchema):
    tenant: it.Int64 = None
    month: it.Date = None
    cash: it.Int8 = None


@frozen
class WholeUnitCashFeatures(WholeUnitBalance, Expression):
    cash__mean_abs_diff_last_2: it.Float64 = None

    @classmethod
    def from_expression(cls, inputs: IbisTable[WholeUnitBalance]):
        cols = inputs.cols
        table = inputs.table @ TimeSeriesFeatureExtraction(
            keys=[cols.tenant],
            order_by=cols.month,
            columns=[cols.cash],
            features=[MeanAbsDiff()],
            windows=[2],
        )
        return cls.of(table)


@frozen
class ObservedBalance(IbisSchema):
    tenant: it.Int64 = None
    observation_month: it.Date = None
    month: it.Date = None
    cash: it.Float64 = None


@frozen
class ObservedCashSpectralFeatures(ObservedBalance, Expression):
    cash__n_unique_last_3: it.Int64 = None
    cash__median_frequency_last_3: it.Float64 = None
    cash__n_unique_last_4: it.Int64 = None
    cash__median_frequency_last_4: it.Float64 = None

    @classmethod
    def from_expression(cls, inputs: IbisTable[ObservedBalance]):
        cols = inputs.cols
        table = inputs.table @ TimeSeriesFeatureExtraction(
            keys=[cols.tenant, cols.observation_month],
            order_by=cols.month,
            columns=[cols.cash],
            features=[NUnique(), MedianFrequency()],
            windows=(3, 4),
            # Monthly samples, so frequencies are in cycles per year.
            sampling_frequency=12.0,
        )
        return cls.of(table)


@frozen
class Cash(IbisSchema):
    month: it.Date = None
    cash: it.Float64 = None


@frozen
class UnkeyedCashFeatures(Cash, Expression):
    cash__sum_last_3: it.Float64 = None
    cash__n_unique_last_3: it.Int64 = None
    cash__median_frequency_last_3: it.Float64 = None

    @classmethod
    def from_expression(cls, inputs: IbisTable[Cash]):
        cols = inputs.cols
        table = inputs.table @ TimeSeriesFeatureExtraction(
            keys=[],
            order_by=cols.month,
            columns=[cols.cash],
            features=[Sum(), NUnique(), MedianFrequency()],
            windows=[3],
            sampling_frequency=12.0,
        )
        return cls.of(table)


def test_without_keys_the_whole_table_is_one_series(evaluate_table):
    def iter_rows():
        yield Cash(month=JANUARY, cash=3.0)
        yield Cash(month=FEBRUARY, cash=1.0)
        yield Cash(month=MARCH, cash=4.0)
        yield Cash(month=APRIL, cash=1.0)

        # Expected
        yield UnkeyedCashFeatures(month=JANUARY, cash=3.0)
        yield UnkeyedCashFeatures(month=FEBRUARY, cash=1.0)
        yield UnkeyedCashFeatures(
            month=MARCH,
            cash=4.0,
            cash__sum_last_3=8.0,
            cash__n_unique_last_3=3,
            cash__median_frequency_last_3=4.0,
        )
        yield UnkeyedCashFeatures(
            month=APRIL,
            cash=1.0,
            cash__sum_last_3=6.0,
            cash__n_unique_last_3=2,
            cash__median_frequency_last_3=4.0,
        )

    actual, expected = evaluate_table(UnkeyedCashFeatures, iter_rows())
    assert actual == expected


def test_each_month_gets_the_features_of_itself_and_the_previous_month(
    evaluate_table,
):
    def iter_rows():
        yield Balance(tenant=123, month=JANUARY, monetary_amount=10.0, currency="SEK")
        yield Balance(tenant=123, month=FEBRUARY, monetary_amount=12.0, currency="SEK")
        yield Balance(tenant=123, month=MARCH, monetary_amount=9.0, currency="SEK")
        yield Balance(tenant=123, month=APRIL, monetary_amount=15.0, currency="SEK")

        # Expected
        yield CashFeatures(
            tenant=123, month=JANUARY, monetary_amount=10.0, currency="SEK"
        )
        yield CashFeatures(
            tenant=123,
            month=FEBRUARY,
            monetary_amount=12.0,
            currency="SEK",
            cash__sum_last_2_months=22.0,
            cash__mean_abs_diff_last_2_months=2.0,
        )
        yield CashFeatures(
            tenant=123,
            month=MARCH,
            monetary_amount=9.0,
            currency="SEK",
            cash__sum_last_2_months=21.0,
            cash__mean_abs_diff_last_2_months=3.0,
        )
        yield CashFeatures(
            tenant=123,
            month=APRIL,
            monetary_amount=15.0,
            currency="SEK",
            cash__sum_last_2_months=24.0,
            cash__mean_abs_diff_last_2_months=6.0,
        )

    actual, expected = evaluate_table(CashFeatures, iter_rows())
    assert actual == expected


def test_each_tenant_is_its_own_series(evaluate_table):
    def iter_rows():
        yield Balance(tenant=123, month=JANUARY, monetary_amount=10.0)
        yield Balance(tenant=123, month=FEBRUARY, monetary_amount=12.0)
        yield Balance(tenant=123, month=MARCH, monetary_amount=9.0)
        yield Balance(tenant=234, month=FEBRUARY, monetary_amount=5.0)
        yield Balance(tenant=234, month=MARCH, monetary_amount=5.0)
        yield Balance(tenant=345, month=MARCH, monetary_amount=7.0)

        # Expected
        yield CashFeatures(tenant=123, month=JANUARY, monetary_amount=10.0)
        yield CashFeatures(
            tenant=123,
            month=FEBRUARY,
            monetary_amount=12.0,
            cash__sum_last_2_months=22.0,
            cash__mean_abs_diff_last_2_months=2.0,
        )
        yield CashFeatures(
            tenant=123,
            month=MARCH,
            monetary_amount=9.0,
            cash__sum_last_2_months=21.0,
            cash__mean_abs_diff_last_2_months=3.0,
        )
        yield CashFeatures(tenant=234, month=FEBRUARY, monetary_amount=5.0)
        yield CashFeatures(
            tenant=234,
            month=MARCH,
            monetary_amount=5.0,
            cash__sum_last_2_months=10.0,
            cash__mean_abs_diff_last_2_months=0.0,
        )
        yield CashFeatures(tenant=345, month=MARCH, monetary_amount=7.0)

    actual, expected = evaluate_table(CashFeatures, iter_rows())
    assert actual == expected


def test_later_months_do_not_change_earlier_results(evaluate_table):
    def iter_rows():
        # The same first two months; only March differs.
        yield Balance(tenant=123, month=JANUARY, monetary_amount=10.0)
        yield Balance(tenant=123, month=FEBRUARY, monetary_amount=12.0)
        yield Balance(tenant=123, month=MARCH, monetary_amount=9.0)
        yield Balance(tenant=234, month=JANUARY, monetary_amount=10.0)
        yield Balance(tenant=234, month=FEBRUARY, monetary_amount=12.0)
        yield Balance(tenant=234, month=MARCH, monetary_amount=999.0)

        # Expected
        for tenant in (123, 234):
            yield CashFeatures(tenant=tenant, month=JANUARY, monetary_amount=10.0)
            yield CashFeatures(
                tenant=tenant,
                month=FEBRUARY,
                monetary_amount=12.0,
                cash__sum_last_2_months=22.0,
                cash__mean_abs_diff_last_2_months=2.0,
            )
        yield CashFeatures(
            tenant=123,
            month=MARCH,
            monetary_amount=9.0,
            cash__sum_last_2_months=21.0,
            cash__mean_abs_diff_last_2_months=3.0,
        )
        yield CashFeatures(
            tenant=234,
            month=MARCH,
            monetary_amount=999.0,
            cash__sum_last_2_months=1011.0,
            cash__mean_abs_diff_last_2_months=987.0,
        )

    actual, expected = evaluate_table(CashFeatures, iter_rows())
    assert actual == expected


def test_months_are_ordered_by_month_not_by_row_order(evaluate_table):
    def iter_rows():
        yield Balance(tenant=123, month=MARCH, monetary_amount=4.0)
        yield Balance(tenant=123, month=JANUARY, monetary_amount=1.0)
        yield Balance(tenant=123, month=FEBRUARY, monetary_amount=2.0)

        # Expected
        yield CashFeatures(tenant=123, month=JANUARY, monetary_amount=1.0)
        yield CashFeatures(
            tenant=123,
            month=FEBRUARY,
            monetary_amount=2.0,
            cash__sum_last_2_months=3.0,
            cash__mean_abs_diff_last_2_months=1.0,
        )
        yield CashFeatures(
            tenant=123,
            month=MARCH,
            monetary_amount=4.0,
            cash__sum_last_2_months=6.0,
            cash__mean_abs_diff_last_2_months=2.0,
        )

    actual, expected = evaluate_table(CashFeatures, iter_rows())
    assert actual == expected


def test_every_feature_is_computed_for_every_window(evaluate_table):
    def iter_rows():
        yield Balance(tenant=123, month=JANUARY, monetary_amount=1.0)
        yield Balance(tenant=123, month=FEBRUARY, monetary_amount=2.0)
        yield Balance(tenant=123, month=MARCH, monetary_amount=4.0)
        yield Balance(tenant=123, month=APRIL, monetary_amount=8.0)

        # Expected
        yield CashFeaturesOverTwoWindows(tenant=123, month=JANUARY, monetary_amount=1.0)
        yield CashFeaturesOverTwoWindows(
            tenant=123,
            month=FEBRUARY,
            monetary_amount=2.0,
            cash__sum_last_2=3.0,
            cash__mean_abs_diff_last_2=1.0,
        )
        yield CashFeaturesOverTwoWindows(
            tenant=123,
            month=MARCH,
            monetary_amount=4.0,
            cash__sum_last_2=6.0,
            cash__mean_abs_diff_last_2=2.0,
            cash__sum_last_3=7.0,
            cash__mean_abs_diff_last_3=1.5,
        )
        yield CashFeaturesOverTwoWindows(
            tenant=123,
            month=APRIL,
            monetary_amount=8.0,
            cash__sum_last_2=12.0,
            cash__mean_abs_diff_last_2=4.0,
            cash__sum_last_3=14.0,
            cash__mean_abs_diff_last_3=3.0,
        )

    actual, expected = evaluate_table(CashFeaturesOverTwoWindows, iter_rows())
    assert actual == expected


def test_a_window_longer_than_the_series_is_null_everywhere(evaluate_table):
    def iter_rows():
        yield Balance(tenant=123, month=JANUARY, monetary_amount=1.0)
        yield Balance(tenant=123, month=FEBRUARY, monetary_amount=2.0)

        # Expected
        yield CashFeaturesOverTwoWindows(tenant=123, month=JANUARY, monetary_amount=1.0)
        yield CashFeaturesOverTwoWindows(
            tenant=123,
            month=FEBRUARY,
            monetary_amount=2.0,
            cash__sum_last_2=3.0,
            cash__mean_abs_diff_last_2=1.0,
        )

    actual, expected = evaluate_table(CashFeaturesOverTwoWindows, iter_rows())
    assert actual == expected


def test_every_value_column_gets_every_feature_and_window(evaluate_table):
    def iter_rows():
        yield CashAndDebt(tenant=123, month=JANUARY, cash=10.0, debt=4.0)
        yield CashAndDebt(tenant=123, month=FEBRUARY, cash=12.0, debt=0.0)
        yield CashAndDebt(tenant=123, month=MARCH, cash=9.0, debt=4.0)

        # Expected
        yield CashAndDebtFeatures(tenant=123, month=JANUARY, cash=10.0, debt=4.0)
        yield CashAndDebtFeatures(
            tenant=123,
            month=FEBRUARY,
            cash=12.0,
            debt=0.0,
            cash__sum_last_2=22.0,
            cash__mean_abs_diff_last_2=2.0,
            debt__sum_last_2=4.0,
            debt__mean_abs_diff_last_2=4.0,
        )
        yield CashAndDebtFeatures(
            tenant=123,
            month=MARCH,
            cash=9.0,
            debt=4.0,
            cash__sum_last_2=21.0,
            cash__mean_abs_diff_last_2=3.0,
            debt__sum_last_2=4.0,
            debt__mean_abs_diff_last_2=4.0,
            cash__sum_last_3=31.0,
            cash__mean_abs_diff_last_3=2.5,
            debt__sum_last_3=8.0,
            debt__mean_abs_diff_last_3=4.0,
        )

    actual, expected = evaluate_table(CashAndDebtFeatures, iter_rows())
    assert actual == expected


def test_integer_value_columns_do_not_overflow(evaluate_table):
    def iter_rows():
        yield WholeUnitBalance(tenant=123, month=JANUARY, cash=100)
        yield WholeUnitBalance(tenant=123, month=FEBRUARY, cash=-100)
        yield WholeUnitBalance(tenant=123, month=MARCH, cash=127)

        # Expected: steps beyond the int8 range, and cash itself still int8.
        yield WholeUnitCashFeatures(tenant=123, month=JANUARY, cash=100)
        yield WholeUnitCashFeatures(
            tenant=123, month=FEBRUARY, cash=-100, cash__mean_abs_diff_last_2=200.0
        )
        yield WholeUnitCashFeatures(
            tenant=123, month=MARCH, cash=127, cash__mean_abs_diff_last_2=227.0
        )

    actual, expected = evaluate_table(WholeUnitCashFeatures, iter_rows())
    assert actual == expected


def test_spectral_features_per_tenant_and_observation_month(evaluate_table):
    # Each (tenant, observation month) is its own series of cash per month, with
    # the expected nunique and median frequency over the last 3 and 4 months. The
    # frequencies are k · 12 / window cycles per year: 4 for 3 months, 3 or 6 for 4.
    series = {
        (123, JANUARY): [
            (3.0, None, None, None, None),
            (1.0, None, None, None, None),
            (4.0, 3, 4.0, None, None),
            (1.0, 2, 4.0, 3, 6.0),
            (5.0, 3, 4.0, 3, 6.0),
            (9.0, 3, None, 4, 3.0),  # [1, 5, 9] is a line, without frequency.
        ],
        (123, FEBRUARY): [
            (2.0, None, None, None, None),
            (7.0, None, None, None, None),
            (1.0, 3, 4.0, None, None),
            (8.0, 3, 4.0, 4, 6.0),
            (3.0, 3, 4.0, 4, 6.0),
        ],
        (234, JANUARY): [
            (5.0, None, None, None, None),
            (-3.0, None, None, None, None),
            (0.0, 3, 4.0, None, None),
            (6.0, 3, 4.0, 4, 3.0),
        ],
        (234, FEBRUARY): [
            (1.0, None, None, None, None),
            (2.0, None, None, None, None),
        ],
    }

    def iter_rows():
        for (tenant, observation_month), points in series.items():
            for index, point in enumerate(points):
                cash, nunique_3, frequency_3, nunique_4, frequency_4 = point
                month = date(2023, 7 + index, 1)
                yield ObservedBalance(
                    tenant=tenant,
                    observation_month=observation_month,
                    month=month,
                    cash=cash,
                )
                yield ObservedCashSpectralFeatures(
                    tenant=tenant,
                    observation_month=observation_month,
                    month=month,
                    cash=cash,
                    cash__n_unique_last_3=nunique_3,
                    cash__median_frequency_last_3=frequency_3,
                    cash__n_unique_last_4=nunique_4,
                    cash__median_frequency_last_4=frequency_4,
                )

    actual, expected = evaluate_table(ObservedCashSpectralFeatures, iter_rows())
    assert actual == expected
