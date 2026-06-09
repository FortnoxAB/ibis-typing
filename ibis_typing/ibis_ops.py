"""Provides ibis.Value -> ibis.Value functions for custom operations."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any, cast

import ibis
from ibis import Table, Value, ir
from typing_extensions import deprecated

from .custom import custom_operations
from .custom.op_cast import op_cast
from .ibis_extension_method import ValueMethod


class ColumnChecksum(ValueMethod[Value, ir.IntegerValue]):
    def apply(self, value):
        return custom_operations.ColumnChecksum(arg=op_cast(value)).to_expr()


def literal_table(name: str, rows: Iterable, schema: ibis.Schema) -> Table:
    return custom_operations.LiteralTable.from_rows(
        rows,
        schema=schema,
        name=name,
    ).to_expr()


class JsonParse(ValueMethod[ir.StringValue, ir.JSONValue]):
    def apply(self, value: ir.StringValue):
        return custom_operations.JsonParse(arg=cast(Any, value)).to_expr()


class JsonFormat(ValueMethod[ir.JSONValue, ir.StringValue]):
    """
    Format a JSON object as a string.

    Since .cast("string") is handled differently for JSON objects for different backends,
    this operation ensures that objects can be converted to strings for all backends.
    """

    def apply(self, value: ir.JSONValue):
        return custom_operations.JsonFormat(arg=op_cast(value)).to_expr()


class IntToUUID(ValueMethod[ir.IntegerValue, ir.UUIDValue]):
    """Convert Int64 to UUID."""

    def apply(self, value: ir.IntegerValue):
        return custom_operations.UUIDFromInt(arg=op_cast(value)).to_expr()


class LuhnCheck(ValueMethod[ir.StringValue, ir.BooleanValue]):
    """
    Validate a string using the Luhn algorithm (e.g., credit card numbers).

    Trino has a built-in luhn_check() function. DuckDB uses a custom implementation
    that splits the string, reverses it, doubles every second digit, and checks
    if the sum modulo 10 equals 0.
    """

    def apply(self, value: ir.StringValue):
        return custom_operations.LuhnCheck(arg=op_cast(value)).to_expr()


@deprecated("Use `value @ ColumnChecksum()` instead")
def column_checksum(value: Value) -> ir.IntegerValue:
    return value @ ColumnChecksum()


@deprecated("Use `value @ JsonParse()` instead")
def parse_json(value: ir.StringValue) -> ir.JSONValue:
    return value @ JsonParse()


@deprecated("Use `value @ JsonFormat()` instead")
def json_format(value: ir.JSONValue) -> ir.StringValue:
    return value @ JsonFormat()


@deprecated("Use `value @ IntToUUID()` instead")
def uuid_from_int(value: ir.IntegerValue) -> ir.UUIDValue:
    return value @ IntToUUID()


@deprecated("Use `value @ LuhnCheck()` instead")
def luhn_check(value: ir.StringValue) -> ir.BooleanValue:
    return value @ LuhnCheck()
