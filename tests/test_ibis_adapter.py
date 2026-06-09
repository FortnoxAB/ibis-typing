import decimal
import uuid
from collections.abc import Mapping
from typing import TypedDict

import ibis
import pytest
from attrs import frozen

from ibis_typing import (
    Expression,
    IbisSchema,
    IbisTable,
    it,
    this,
)
from ibis_typing.fixtures import marks
from ibis_typing.ibis_utils import Aggregate, Select
from ibis_typing.table_provider import (
    get_abstract_table,
    get_empty_table,
)
from ibis_typing.utils import StrDate


@frozen
class Schema(IbisSchema):
    float: it.Float64 = None
    integer: it.Int64 = None
    decimal: it.Decimal = None
    text: it.String = None
    date: it.Date = None
    timestamp: it.Timestamp = None
    uuid: it.UUID = None
    array: it.Array[it.String] = None
    mapping: it.Map[it.String, it.Int64] = None


@frozen
class InputTable(IbisSchema):
    input_id: it.String = None


@frozen
class OutputTable(Expression):
    output_id: it.String = None

    @classmethod
    def from_expression(cls, inputs: IbisTable[InputTable]):
        table = inputs.table.rename({"output_id": inputs.cols.input_id})
        return cls.of(table)


@frozen
class ArrayTable(Expression):
    output_ids: it.Array[it.JSON] = None

    @classmethod
    def from_expression(cls, inputs: IbisTable[InputTable]):
        col = inputs.cols
        table = inputs.table @ Aggregate(
            by=[], expr={"output_ids": this[col.input_id].collect()}
        )
        return cls.of(table)


class ArrayOutputTable(ArrayTable):
    @classmethod
    def from_expression(cls, inputs: IbisTable[ArrayTable]):  # type: ignore
        return cls.of(inputs.table)


@frozen
class SuperTable(Expression):
    super_id: it.String = None

    @classmethod
    def from_expression(cls, outputs: IbisTable[OutputTable]):
        table = outputs.table.rename({"super_id": outputs.cols.output_id})
        return cls.of(table)


datetime = StrDate("2020-01-01").datetime
data = [
    Schema(
        float=123.45,
        integer=12,
        decimal=decimal.Decimal("0.000"),
        text="Text",
        date=datetime.date(),
        timestamp=datetime,
        uuid=uuid.UUID(int=1),
        array=["a", "b"],
        mapping={"c": 1, "d": 2},
    )
]


def test_fetch_table_of_rows(fetch_table):
    table = Schema.of_rows(data)
    assert fetch_table(table) == data


def test_fetch_table_without_rows(fetch_table):
    table = Schema.of_rows([])
    assert fetch_table(table) == []


def test_fetch_table_from_empty_table_provider(fetch_table):
    table = get_empty_table(Schema)
    assert fetch_table(table) == []


def test_fetch_abstract_table_raises_error(fetch_table):
    table = get_abstract_table(Schema)
    with pytest.raises(Exception):
        fetch_table(table)


def test_fetch_table_expression(fetch_table):
    rows = [InputTable(input_id="1")]
    expected = [OutputTable(output_id="1")]

    inputs = InputTable.of_rows(rows)
    table = OutputTable.from_expression(inputs)

    actual = fetch_table(table)
    assert actual == expected


def test_struct_table_raises_TypeError(fetch_table):
    @frozen
    class MyStruct(Expression):
        class Inner(TypedDict):
            value: it.String

        inner: it.Struct[Inner] = None

        @classmethod
        def from_expression(cls, inputs: IbisTable[InputTable]):
            table = inputs.table @ Select(
                expr={"inner": ibis.struct({"value": this[inputs.cols.input_id]})},
            )
            return cls.of(table)

    rows = [MyStruct()]

    with pytest.raises(TypeError):
        MyStruct.of_rows(rows)

    table = MyStruct.from_expression(InputTable.of_rows([]))
    with pytest.raises(TypeError):
        fetch_table(table)


def test_evaluate_table(evaluate_table):
    rows = iter([OutputTable(output_id="1"), InputTable(input_id="1")])

    actual, expected = evaluate_table(OutputTable, rows)

    assert actual == expected


def test_evaluate_table_raises_error_when_having_unused_inputs(evaluate_table):
    rows = [OutputTable(output_id="1"), Schema(text="2")]

    with pytest.raises(ValueError):
        evaluate_table(OutputTable, rows)


def test_evaluate_table_can_construct_intermediate_input_expressions(
    evaluate_table,
):
    rows = iter([SuperTable(super_id="1"), InputTable(input_id="1")])

    actual, expected = evaluate_table(SuperTable, rows)

    assert actual == expected


def test_evaluate_table_raises_error_when_missing_inputs(evaluate_table):
    rows = [SuperTable(super_id="1")]

    with pytest.raises(ValueError) as e:
        evaluate_table(SuperTable, rows)

    expected_message = """
Missing input schema. Trace input -> output:
	tests.test_ibis_adapter.InputTable
	tests.test_ibis_adapter.OutputTable
	tests.test_ibis_adapter.SuperTable
	""".strip()
    assert e.value.args[0] == expected_message


def test_evaluate_table_uses_cache_for_calculated_expressions(evaluate_table):
    @frozen
    class Input(IbisSchema):
        val: it.Int64

    @frozen
    class Intermediate(Input, Expression):
        calls = 0

        @classmethod
        def _get_table_schema(cls) -> Mapping[str, str]:
            return Input._get_table_schema()

        @classmethod
        def from_expression(cls, inputs: IbisTable[Input]):
            cls.calls += 1
            return cls.of(inputs.table)

    @frozen
    class Upper(Input, Expression):
        @classmethod
        def from_expression(cls, inputs: IbisTable[Intermediate]):
            return cls.of(inputs.table)

    @frozen
    class Output(Input, Expression):
        @classmethod
        def from_expression(
            cls, inputs: IbisTable[Intermediate], upper: IbisTable[Upper]
        ):
            return cls.of(upper.table)

    rows = [Output(val=1), Input(val=1)]

    Intermediate.calls = 0
    actual, expected = evaluate_table(Output, rows)
    assert actual == expected
    assert Intermediate.calls == 1


@marks.use_backend_duckdb
def test_fetch_read_and_write_parquet(tmp_path, ibis_connection):
    path = tmp_path / "data.parquet"
    expected_table = Schema.of_rows(data)

    expected = list(ibis_connection.fetch_table(expected_table))

    assert expected == data

    ibis_connection.write_parquet(expected_table, path=path)
    actual_table = ibis_connection.read_parquet(path, cls=Schema)

    actual = list(ibis_connection.fetch_table(actual_table))

    assert actual == expected
