"""Implements SQLGlotCompiler support for LiteralTable operations."""

from __future__ import annotations

import ibis
import sqlglot.expressions as sg
from ibis.backends.sql.compilers.base import SQLGlotCompiler

from .. import custom_operations

__all__ = ["LiteralTableCompiler", "compiler_extension"]


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
