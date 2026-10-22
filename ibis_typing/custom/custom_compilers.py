"""Implements ibis.Backend compiler support for custom_operations.py."""

from typing import Any

import ibis
import ibis.expr.datatypes as dt
import sqlglot.expressions as sg
from ibis.backends.sql import compilers
from ibis.backends.sql.compilers.base import SQLGlotCompiler
from ibis.expr import operations
from sqlglot.expressions import Identifier

from . import custom_operations


def register_operations():
    # Note: Operations are registered simply by importing this module.
    # This provides an explicit function to trigger the import.
    ...


def compiler_extension[S](cls: type[S]) -> type[S]:
    """Register custom operations on the inherited base compiler class."""
    base = cls.__bases__[0]
    methods = vars(cls)
    for name, method in methods.items():
        if name.startswith("visit_"):
            setattr(base, name, method)

    return cls


@compiler_extension
class LiteralTableCompiler(SQLGlotCompiler):
    """Base SQLGlotCompiler extension for compiling LiteralTable operations."""

    def visit_LiteralTable(
        self,
        op: custom_operations.LiteralTable,
        *,
        data,
        schema: ibis.Schema,
        name: str,
    ):
        values = custom_operations.LiteralTable.to_values(data)
        sql = sg.values(values, alias=name, columns=schema)
        return sg.select("*", copy=False).from_(sql, copy=False)


@compiler_extension
class TrinoCompilerPatch(compilers.TrinoCompiler):
    def visit_Hash(self, op: operations.Hash, *, arg):
        # Note: Trino does not support the has function by default. Extend to support integer hashing.
        return self.f.from_big_endian_64(self.f.xxhash64(arg))


@compiler_extension
class TrinoCompiler(compilers.TrinoCompiler):
    agg: Any

    def visit_ColumnChecksum(self, op: custom_operations.ColumnChecksum, *, arg, where):
        return self.f.from_big_endian_64(self.agg.checksum(arg, where=where))

    def visit_DateAddMonth(self, op: custom_operations.DateAddMonth, *, left, right):
        return self.f.date_add("month", right, left)

    def visit_DateAddDay(self, op: custom_operations.DateAddDay, *, left, right):
        return self.f.date_add("day", right, left)

    def visit_JsonParse(self, op: custom_operations.JsonParse, *, arg):
        return self.f.json_parse(arg)

    def visit_JsonFormat(self, op: custom_operations.JsonFormat, *, arg):
        return self.f.json_format(arg)

    def visit_UUIDFromInt(self, op: custom_operations.UUIDFromInt, *, arg):
        int64 = self.f.to_big_endian_64(arg)
        int128 = self.f.lpad(int64, 16, bytes(8))
        return self.cast(int128, dt.UUID())

    def visit_LuhnCheck(self, op: custom_operations.LuhnCheck, *, arg):
        return self.f.luhn_check(arg)


@compiler_extension
class DuckDbCompiler(compilers.DuckDBCompiler):
    agg: Any

    def visit_ColumnChecksum(self, op: custom_operations.ColumnChecksum, *, arg, where):
        checksum = self.agg.bit_xor(self.f.hash(arg), where=where)
        return self.cast(checksum % 2 ** (64 - 1), dt.int64)

    def visit_DateAddMonth(self, op: custom_operations.DateAddMonth, *, left, right):
        return self.cast(left + self.f.to_months(right), dt.date)

    def visit_DateAddDay(self, op: custom_operations.DateAddDay, *, left, right):
        return self.cast(left + self.f.to_days(right), dt.date)

    def visit_JsonParse(self, op: custom_operations.JsonParse, *, arg):
        return self.cast(arg, dt.JSON())

    def visit_JsonFormat(self, op: custom_operations.JsonFormat, *, arg):
        return self.cast(arg, dt.string())

    def visit_UUIDFromInt(self, op: custom_operations.UUIDFromInt, *, arg):
        uuid_str = self.f.lpad(self.f.hex(arg), 32, "0")
        return self.cast(uuid_str, dt.UUID())

    def visit_LuhnCheck(self, op: custom_operations.LuhnCheck, *, arg: sg.Expression):
        def lit(number: int):
            return sg.Literal.number(number=number)

        def to_int(number: Identifier):
            return sg.Cast(this=number, to="INT64")

        def times_two(number: Identifier):
            return sg.Mul(
                this=to_int(number),
                expression=lit(2),
            )

        def is_even(number):
            return sg.Mod(this=number, expression=lit(2)).eq(lit(0))

        digit = sg.to_identifier("digit")

        idx = sg.to_identifier("idx")

        calculate_sum_of_digit_times_2 = sg.If(
            this=sg.GT(
                this=times_two(digit),
                expression=lit(9),
            ),
            true=sg.Sub(
                this=times_two(digit),
                expression=lit(9),
            ),
            false=times_two(digit),
        )

        func = sg.Lambda(
            expressions=[digit, idx],
            this=sg.If(
                this=is_even(idx),
                true=calculate_sum_of_digit_times_2,
                false=to_int(digit),
            ),
        )

        digits = self.f.split(self.f.reverse(arg), "")

        return sg.Mod(
            this=self.f.list_sum(self.f.list_transform(digits, func)),
            expression=lit(10),
        ).eq(lit(0))
