"""Sample writing and reading values from Schema.

Demonstrates compatibility with pyright type checker and IntelliJ IDE.
"""

from __future__ import annotations

from typing import TypedDict

import hypothesis
import ibis
from attrs import frozen
from hypothesis import given
from ibis import ir, literal

from ibis_typing import IbisSchema, it, this
from ibis_typing.hypothesis import strategy_for
from ibis_typing.ibis_adapter import IbisDbSchema
from ibis_typing.ibis_utils import Aggregate, Select
from ibis_typing.table_provider import (
    AbstractTableProvider,
    DbTableProvider,
    EmptyTableProvider,
    get_abstract_table,
)

exhaustive = hypothesis.settings(max_examples=2**5)


@frozen
class SimpleSchema(IbisSchema):
    integer: it.Int64 = None
    float: it.Float64 = None
    boolean: it.Boolean = None
    text: it.String = None
    bytes: it.Binary = None

    decimal: it.Decimal = None
    date: it.Date = None
    time: it.Time = None
    timestamp: it.Timestamp = None


@frozen
class CollectionSchema(IbisSchema):
    array: it.Array[it.Int64] = None
    mapping: it.Map[it.String, it.Int64] = None
    struct: it.Struct[MyStruct] = None
    json: it.JSON = None

    class MyStruct(TypedDict):
        amount: it.Float64
        date: it.Date


@exhaustive
@given(strategy_for(SimpleSchema))
def test_simple_column_typing(fetch_table, data):
    inputs = SimpleSchema.of_rows([data])
    actual = fetch_table(inputs)
    assert actual

    col = SimpleSchema.cols

    _ = inputs.table @ Select(
        expr={
            col.integer: this[col.integer].bit_and(),
            col.float: this[col.float].isnan(),
            col.boolean: this[col.boolean].all(),
            col.text: this[col.text].lower(),
            col.bytes: this[col.bytes].hashbytes(),
            col.decimal: this[col.decimal].pow(literal(1)),
            col.date: this[col.date].day(),
            col.time: this[col.time].time(),
            col.timestamp: this[col.timestamp].day(),
        },
    )


def test_collections_column_typing():
    inputs = get_abstract_table(CollectionSchema)

    col = inputs.cols

    def map_fn(x: ir.Value):
        return x.cast(float)

    def filter_fn(x: ir.Value):
        return x.cast(bool)

    _ = inputs.table @ Select(
        expr={
            col.array: this[col.array].map(map_fn).filter(filter_fn)[0],
            # Note: Unhashable collection types cause type error when used as mapping keys.
            # Easiest solution is to simply wrap the actual string in a str() call.
            str(col.struct): this[col.struct]["amount"],
            str(col.mapping): this[col.mapping].keys(),
            str(col.json): this[col.json]["key"].array[0].float,
        },
    )


@exhaustive
@given(strategy_for(SimpleSchema))
def test_schema_read_write_typing(data: SimpleSchema):
    _ = SimpleSchema(
        # simple
        integer=(v := data.integer) and v**2,
        float=(v := data.float) and v * 2,
        boolean=(v := data.boolean) and v,
        text=(v := data.text) and v.upper(),
        bytes=(v := data.bytes) and v.upper(),
        # Complex
        decimal=(v := data.decimal) and v / 2,
        date=(v := data.date) and v.replace(day=1),
        time=(v := data.time) and v.replace(hour=1),
        timestamp=(v := data.timestamp) and v.replace(year=1),
    )


def test_table_operations():
    inputs = get_abstract_table(SimpleSchema)

    col = inputs.cols
    d = it.deferred

    _ = (
        inputs.table
        @ d.select(
            col.integer,
            col.float,
            col.timestamp,
            col.decimal,
        )
        @ d.filter(this[col.integer] > literal(0))
        @ Aggregate(
            by=[col.integer, col.timestamp],
            sum=[col.decimal],
            arbitrary=[col.float],
        )
        @ d.cast({col.decimal: int})
        @ d.rename({col.integer: col.decimal})
        @ d.drop(col.integer, col.timestamp)
        @ d.order_by(this[col.float].desc())
        @ d.order_by(ibis.desc(col.float))
        @ d.order_by(col.float)
        @ d.order_by("float")
    )


def test_table_provider_overloads():
    @frozen
    class MyDbSchema(IbisDbSchema):
        table_name = "my_table"
        table_namespace = "my", "namespace"

        value: it.Int64 = None

    db_provider = DbTableProvider()
    empty_provider = EmptyTableProvider()
    abstract_provider = AbstractTableProvider()

    assert db_provider(MyDbSchema).table_schema
    assert empty_provider(MyDbSchema).table_schema
    assert abstract_provider(MyDbSchema).table_schema
