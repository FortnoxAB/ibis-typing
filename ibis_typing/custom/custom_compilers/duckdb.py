"""Implements DuckDBCompiler support for custom_operations.py."""

from __future__ import annotations

from typing import Any

import ibis.expr.datatypes as dt
import sqlglot.expressions as sg
from ibis.backends.sql import compilers
from sqlglot.expressions import Identifier

from .. import custom_operations
from .core import compiler_extension

__all__ = ["DuckDbCompiler"]


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
