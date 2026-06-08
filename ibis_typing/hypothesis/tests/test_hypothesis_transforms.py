"""Sample Hypothesis-based tests of simple aggregate Ibis expression."""

import datetime

from attrs import frozen
from hypothesis import given
from hypothesis import strategies as st

from ibis_typing import (
    Expression,
    IbisSchema,
    IbisTable,
    it,
    this,
    utils,
)
from ibis_typing.hypothesis import strategy_for
from ibis_typing.ibis_time import StartOfMonth
from ibis_typing.ibis_utils import Aggregate, Select


# Define input Ibis schema.
@frozen
class Transaction(IbisSchema):
    date: it.Date
    amount: it.Float64


# Define Ibis expression unit-under-test.
@frozen
class MonthlyAmounts(Expression):
    month: it.Date
    amount: it.Float64

    @classmethod
    def from_expression(cls, inputs: IbisTable[Transaction]):
        cols = inputs.cols

        table = (
            inputs.table
            @ Select(expr={"month": this[cols.date] @ StartOfMonth()})
            @ Aggregate(by=["month"], sum=[cols.amount])
        )

        return cls.of(table)


# Test Ibis output against Python reference implementation.
@given(st.lists(strategy_for(Transaction), min_size=1))
def test_sums_transactions_by_month(evaluate_table, transactions: list[Transaction]):
    transactions_by_month = utils.group_by(
        transactions,
        key=lambda x: x.date and datetime.date(x.date.year, x.date.month, 1),
    ).items()
    outputs = [
        MonthlyAmounts(month=month, amount=sum(t.amount or 0 for t in transactions))
        for month, transactions in transactions_by_month
    ]
    assert outputs

    actual, expected = evaluate_table(MonthlyAmounts, transactions + outputs)

    assert actual == expected


# Test Ibis output given explicit example input.
def test_sums_transactions_by_month_without_hypothesis(evaluate_table):
    today = utils.StrDate("2021-01-01")
    inputs = [
        Transaction(date=today.date, amount=1.0),
        Transaction(date=today.plus(1).date, amount=2.0),
    ]
    outputs = [
        MonthlyAmounts(month=today.date, amount=sum(row.amount or 0 for row in inputs)),
    ]

    actual, expected = evaluate_table(MonthlyAmounts, inputs + outputs)

    assert actual == expected


@frozen
class Input(IbisSchema):
    str_id: it.String = None


# Test strategy_for with unique string values.
@given(st.lists(strategy_for(t := Input, uniques=[t.cols.str_id]), min_size=1))
def test_unique_values_for_ibis_strings(evaluate_table, rows: list[Input]):
    @frozen
    class Transform(Expression):
        str_id: it.String = None

        @classmethod
        def from_expression(cls, inputs: IbisTable[Input]):
            table = inputs.table @ Aggregate(by=[inputs.cols.str_id])
            return cls.of(table)

    def iter_rows():
        for row in rows:
            yield row
            yield Transform(row.str_id)

    actual, expected = evaluate_table(Transform, iter_rows())
    assert actual == expected
