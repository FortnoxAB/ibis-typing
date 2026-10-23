"""Implements TrinoCompiler support for custom_operations.py."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, override

import ibis.expr.datatypes as dt
import sqlglot.expressions as sg
from ibis.backends.sql import compilers
from ibis.expr import operations

from .. import custom_operations
from .core import compiler_extension

__all__ = ["TrinoCompiler", "TrinoCompilerPatch"]


@compiler_extension
class TrinoCompilerPatch(compilers.TrinoCompiler):
    def visit_Hash(self, op: operations.Hash, *, arg: sg.Expression):
        # Note: Trino does not support the hash function by default.
        # Extend to support integer hashing.
        return self.f.from_big_endian_64(self.f.xxhash64(arg))


@compiler_extension
class TrinoCompiler(compilers.TrinoCompiler):
    if TYPE_CHECKING:
        # The inherited AggGen descriptor returns an untyped attribute accessor.
        @property
        @override
        def agg(self) -> Any: ...

    def visit_ColumnChecksum(
        self,
        op: custom_operations.ColumnChecksum,
        *,
        arg: sg.Expression,
        where: sg.Expression,
    ):
        return self.f.from_big_endian_64(self.agg.checksum(arg, where=where))

    def visit_DateAddMonth(
        self,
        op: custom_operations.DateAddMonth,
        *,
        left: sg.Expression,
        right: sg.Expression,
    ):
        return self.f.date_add("month", right, left)

    def visit_DateAddDay(
        self,
        op: custom_operations.DateAddDay,
        *,
        left: sg.Expression,
        right: sg.Expression,
    ):
        return self.f.date_add("day", right, left)

    def visit_JsonParse(self, op: custom_operations.JsonParse, *, arg: sg.Expression):
        return self.f.json_parse(arg)

    def visit_JsonFormat(self, op: custom_operations.JsonFormat, *, arg: sg.Expression):
        return self.f.json_format(arg)

    def visit_UUIDFromInt(
        self, op: custom_operations.UUIDFromInt, *, arg: sg.Expression
    ):
        int64 = self.f.to_big_endian_64(arg)
        int128 = self.f.lpad(int64, 16, bytes(8))
        return self.cast(int128, dt.UUID())

    def visit_LuhnCheck(self, op: custom_operations.LuhnCheck, *, arg: sg.Expression):
        return self.f.luhn_check(arg)
