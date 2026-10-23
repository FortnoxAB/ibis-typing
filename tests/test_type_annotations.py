"""Sample writing and reading values from Schema.

Demonstrates compatibility with type checker and IntelliJ IDE.
"""

from __future__ import annotations

from typing import TypedDict, assert_type

import hypothesis
from attrs import frozen
from hypothesis import given
from ibis import ir, literal

from ibis_typing import IbisSchema, it, this
from ibis_typing.hypothesis import strategy_for
from ibis_typing.ibis_adapter import IbisDbSchema
from ibis_typing.ibis_api import Desc
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
            # ty promotes `float` to `int | float`, matching the Integer overload too.
            col.float: this[col.float].isnan(),  # ty:ignore[unresolved-attribute]
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
            col.struct: this[col.struct]["amount"] @ it.defer(float).isnan(),
            col.mapping: this[col.mapping].keys(),
            col.json: this[col.json]["key"].array[0] @ it.defer(it.JSON).float,
        },
    )


def test_defer_alias_typing():
    # Statically checked by the type checkers; assert_type is a no-op at runtime.
    assert_type(it.defer(it.Boolean), ir.BooleanValue)
    assert_type(it.defer(it.Int8), ir.IntegerValue)
    assert_type(it.defer(it.UInt64), ir.IntegerValue)
    assert_type(it.defer(it.Float64), ir.FloatingValue)
    assert_type(it.defer(it.String), ir.StringValue)
    assert_type(it.defer(it.Binary), ir.BinaryValue)
    assert_type(it.defer(it.Decimal), ir.DecimalValue)
    assert_type(it.defer(it.Timestamp), ir.TimestampValue)
    assert_type(it.defer(it.Date), ir.DateValue)
    assert_type(it.defer(it.Time), ir.TimeValue)
    assert_type(it.defer(it.UUID), ir.UUIDValue)
    assert_type(it.defer(it.Array[it.Int64]), ir.ArrayValue)
    assert_type(it.defer(it.Map[it.String, it.Int64]), ir.MapValue)
    assert_type(it.defer(it.Struct[CollectionSchema.MyStruct]), ir.StructValue)
    assert_type(it.defer(it.JSON), ir.JSONValue)


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
        @ d.order_by(this[col.float] @ Desc())
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
