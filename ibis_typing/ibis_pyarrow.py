"""Implements IbisTable -> list[IbisSchema] interface.

Implement reading Python IbisSchema instances from an IbisTable expression.
Provides a type compatibility layer between Python, Ibis, and PyArrow.
"""

from __future__ import annotations

import json
import logging
import uuid
from collections.abc import Iterable, Sequence
from typing import Any, cast

import attrs
import ibis
import pyarrow
from attrs import frozen
from ibis import Column, Table, Value, ir
from ibis.expr import datatypes as dt
from ibis.expr import operations
from typing_extensions import deprecated

from . import IbisSchema, IbisTable, ibis_ops, utils
from .custom.op_cast import op_cast
from .ibis_extension_method import TableMethod, ValueMethod
from .ibis_ops import JsonFormat, JsonParse

STRUCT_NOT_SUPPORTED = "Struct values are not supported. Convert to supported types."

logger = logging.getLogger(__name__)


@frozen
class EvaluateExpr:
    connection: ibis.BaseBackend | None = None

    def __rmatmul__(self, expr: ibis.Expr) -> Any:
        if isinstance(expr, Table):
            columns = expr.columns
            rows = expr @ EvaluateTable(self.connection)
            return [dict(zip(columns, row)) for row in rows]

        assert isinstance(expr, Value)
        return expr @ EvaluateValue(self.connection)


@frozen
class EvaluateValue:
    connection: ibis.BaseBackend | None = None

    def __rmatmul__(self, expr: Value) -> Any:
        backend = self.connection or expr._find_backend(use_default=True)
        value = expr @ ValueToArrowCompat(expr.type())

        if isinstance(expr, Column):
            batches: Iterable[pyarrow.RecordBatch] = backend.to_pyarrow_batches(
                value, chunk_size=1_000
            )
            values = (val for batch in batches for val in batch.to_pylist())
            return [val @ PyFromArrowCompat(expr.type()) for val in values]

        arrow_obj = cast(pyarrow.Scalar, backend.to_pyarrow(value))
        return arrow_obj.as_py() @ PyFromArrowCompat(expr.type())


@frozen
class EvaluateIbisTable:
    connection: ibis.BaseBackend | None = None

    def __rmatmul__[T: IbisSchema](self, table: IbisTable[T]) -> Iterable[T]:
        rows = table.table @ EvaluateTable(backend=self.connection)
        yield from (table.table_schema(*row) for row in rows)


@frozen
class EvaluateTable:
    backend: ibis.BaseBackend | None = None
    chunk_size: int = 1_000

    def __rmatmul__(self, table: ir.Table) -> Iterable[tuple]:
        backend = self.backend or table._find_backend(use_default=True)
        compat = table @ TableToArrowCompat()

        batches: Iterable[pyarrow.RecordBatch] = backend.to_pyarrow_batches(
            compat, chunk_size=self.chunk_size
        )
        # Transpose column-based to row-based
        rows = (row for batch in batches for row in zip(*batch.to_pydict().values()))
        yield from (row @ TupleFromArrowCompat(table.schema()) for row in rows)


@deprecated("Use `rows @ LiteralTableFromRows()`")
def as_literal_table(
    rows: Sequence[IbisSchema], *, name: str | None = None
) -> ibis.Table:
    return rows @ LiteralTableFromRows(name)


@frozen
class LiteralTableFromRows:
    name: str | None = None

    def __rmatmul__(self, rows: Sequence[IbisSchema]) -> ibis.Table:
        assert rows
        cls = type(rows[0])
        name = self.name or f"{cls.__name__}__{utils.short_hash(rows)}"

        origin = ibis.schema(cls.table_schema)

        data = [attrs.astuple(row) @ TupleToArrowCompat(origin) for row in rows]
        schema = (ibis.table(origin) @ TableToArrowCompat()).schema()

        table = ibis_ops.literal_table(name, data, schema)

        return table @ TableFromArrowCompat(origin)


@frozen
class TupleToArrowCompat:
    schema: ibis.Schema

    def __rmatmul__(self, other: tuple) -> tuple:
        return tuple(
            val @ PyToArrowCompat(t) for val, t in zip(other, self.schema.values())
        )


@frozen
class TupleFromArrowCompat:
    schema: ibis.Schema

    def __rmatmul__(self, other: tuple) -> tuple:
        return tuple(
            val @ PyFromArrowCompat(t) for val, t in zip(other, self.schema.values())
        )


@frozen
class TableFromArrowCompat(TableMethod):
    schema: ibis.Schema

    def apply(self, table: Table):
        upgrades = {
            col: table[col] @ ValueFromArrowCompat(t) for col, t in self.schema.items()
        }
        return table.mutate(**upgrades)


@frozen
class TableToArrowCompat(TableMethod):
    def apply(self, table: Table):
        downgrades = {
            col: table[col] @ ValueToArrowCompat(t) for col, t in table.schema().items()
        }
        return table.mutate(**downgrades)


@frozen
class PyToArrowCompat:
    typ: dt.DataType

    def __rmatmul__(self, other: Any) -> Any:
        if (value := other) is None:
            return None

        match self.typ:
            case dt.UUID():
                return str(value)
            case dt.JSON():
                return json.dumps(value, indent=None, separators=(",", ":"))
            case dt.Array():
                val_t = cast(dt.DataType, self.typ.value_type)
                val_compat = PyToArrowCompat(val_t)
                return [v @ val_compat for v in value]
            case dt.Map():
                key_t = cast(dt.DataType, self.typ.key_type)
                val_t = cast(dt.DataType, self.typ.value_type)
                key_compat = PyToArrowCompat(key_t)
                val_compat = PyToArrowCompat(val_t)
                return {
                    key @ key_compat: val @ val_compat for key, val in value.items()
                }
            case dt.Struct():
                raise TypeError(STRUCT_NOT_SUPPORTED)
            case _:
                return value


@frozen
class PyFromArrowCompat:
    typ: dt.DataType

    def __rmatmul__(self, other: Any) -> Any:
        if (value := other) is None:
            return None

        match self.typ:
            case dt.UUID():
                return uuid.UUID(value)
            case dt.JSON():
                return json.loads(value)
            case dt.Array():
                val_t = cast(dt.DataType, self.typ.value_type)
                val_compat = PyFromArrowCompat(val_t)
                return [val @ val_compat for val in value]
            case dt.Map():
                key_t = cast(dt.DataType, self.typ.key_type)
                val_t = cast(dt.DataType, self.typ.value_type)
                key_compat = PyFromArrowCompat(key_t)
                val_compat = PyFromArrowCompat(val_t)
                return {key @ key_compat: val @ val_compat for key, val in value}
            case dt.Struct():
                raise TypeError(STRUCT_NOT_SUPPORTED)
            case _:
                return value


@frozen
class ValueFromArrowCompat(ValueMethod):
    typ: dt.DataType

    def apply(self, value):
        match self.typ:
            case dt.UUID():
                assert isinstance(value, ir.StringValue)
                return value.cast(dt.UUID)
            case dt.JSON():
                assert isinstance(value, ir.StringValue)
                return value @ JsonParse()
            case dt.Array():
                assert isinstance(value, ir.ArrayValue)
                val_t = cast(dt.DataType, self.typ.value_type)
                return value.map(ValueFromArrowCompat(val_t).apply)
            case dt.Map():
                assert isinstance(value, ir.MapValue)
                key_t = cast(dt.DataType, self.typ.key_type)
                val_t = cast(dt.DataType, self.typ.value_type)
                return ibis.map(
                    value.keys().map(ValueFromArrowCompat(key_t).apply),
                    value.values().map(ValueFromArrowCompat(val_t).apply),
                )
            case dt.Struct():
                raise TypeError(STRUCT_NOT_SUPPORTED)
            case _:
                return operations.Cast(op_cast(value), to=self.typ).to_expr()


@frozen
class ValueToArrowCompat(ValueMethod):
    typ: dt.DataType

    def apply(self, value):
        match self.typ:
            case dt.UUID():
                assert isinstance(value, ir.UUIDValue)
                return value.cast(str)
            case dt.JSON():
                assert isinstance(value, ir.JSONValue)
                return value @ JsonFormat()
            case dt.Array():
                assert isinstance(value, ir.ArrayValue)
                val_t = cast(dt.DataType, self.typ.value_type)
                return value.map(ValueToArrowCompat(val_t).apply)
            case dt.Map():
                assert isinstance(value, ir.MapValue)
                key_t = cast(dt.DataType, self.typ.key_type)
                val_t = cast(dt.DataType, self.typ.value_type)
                return ibis.map(
                    value.keys().map(ValueToArrowCompat(key_t).apply),
                    value.values().map(ValueToArrowCompat(val_t).apply),
                )
            case dt.Struct():
                raise TypeError(STRUCT_NOT_SUPPORTED)
            case _:
                return operations.Cast(op_cast(value), to=self.typ).to_expr()
