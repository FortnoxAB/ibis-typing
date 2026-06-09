from typing import Any

import cattrs
import pytest
from attrs import frozen
from ibis import literal

from ibis_typing import (
    IbisSchema,
    ibis_utils,
    it,
    this,
)
from ibis_typing.ibis_utils import Aggregate, Select
from tests.conftest import SimpleSchema


def test_select_cols(fetch_table, evaluate_expr):
    @frozen
    class SelectCols(IbisSchema):
        id: it.Int64 = None

    rows = [
        SimpleSchema(id=0, value=2),
        SimpleSchema(id=1, value=3),
    ]
    expected = [
        SelectCols(id=0),
        SelectCols(id=1),
    ]

    table = SimpleSchema.of_rows(rows).table @ Select(SimpleSchema.cols.id)

    actual = fetch_table(SelectCols.of(table))

    assert actual == expected

    table = SimpleSchema.of_rows(rows).table @ Select(drop=[SimpleSchema.cols.value])

    actual = evaluate_expr(table)

    assert actual == cattrs.unstructure(expected)


@pytest.mark.parametrize("selected_cols", [[SimpleSchema.cols.id], []])
def test_select_expr(fetch_table, selected_cols):
    @frozen
    class SelectExpr(SimpleSchema):
        add_one: it.Int64

    rows = [
        SimpleSchema(id=0, value=0),
        SimpleSchema(id=1, value=1),
    ]
    expected = [
        SelectExpr(id=0, value=3, add_one=1),
        SelectExpr(id=1, value=3, add_one=2),
    ]

    table = SimpleSchema.of_rows(rows).table @ Select(
        *selected_cols,
        expr={
            SimpleSchema.cols.value: literal(3),
            "add_one": this[SimpleSchema.cols.value] + literal(1),
        },
    )

    actual = fetch_table(SelectExpr.of(table))

    assert actual == expected


def test_aggregate(fetch_table):
    @frozen
    class AggInputs(IbisSchema):
        id: it.Int64
        arbitrary: it.Int64
        sum: it.Int64
        max: it.Int64

    @frozen
    class AggExpr(AggInputs):
        count: it.Int64

    class AnyOf(Any, list):  # noqa: PLW1641
        def __eq__(self, other):
            return other in self

    rows = [
        AggInputs(id=1, arbitrary=1, sum=2, max=3),
        AggInputs(id=1, arbitrary=4, sum=5, max=6),
    ]
    expected = [
        AggExpr(
            id=1,
            arbitrary=AnyOf([r.arbitrary for r in rows]),
            sum=sum((r.sum or 0) for r in rows),
            max=max(*((r.max or 0) for r in rows)),
            count=len(rows),
        ),
    ]

    table = AggInputs.of_rows(rows).table @ Aggregate(
        by=[AggInputs.cols.id],
        arbitrary=[AggInputs.cols.arbitrary],
        sum=[AggInputs.cols.sum],
        max=[AggInputs.cols.max],
        expr={AggExpr.cols.count: this.count()},
    )

    actual = fetch_table(AggExpr.of(table))

    assert actual == expected


@frozen
class ArraySchema(IbisSchema):
    id: it.Int64
    value: it.Float64
    array: it.Array[it.Int64]


def test_fill_nulls(fetch_table):
    rows = [
        ArraySchema(id=0, value=None, array=[0, 0]),
        ArraySchema(id=1, value=1, array=None),
    ]
    expected = [
        ArraySchema(id=0, value=0, array=[0, 0]),
        ArraySchema(id=1, value=1, array=[0, 0]),
    ]

    table = ArraySchema.of_rows(rows).table
    table = ibis_utils.fill_nulls(
        table, default_provider=ibis_utils.numeric_default_provider, array_length=2
    )

    actual = fetch_table(ArraySchema.of(table))

    assert actual == expected
