"""Implements SQLiteCompiler support for custom_operations.py."""

from __future__ import annotations

from typing import Any

import ibis
import sqlglot.expressions as sg
from ibis.backends.sql import compilers

from .. import custom_operations
from .core import compiler_extension

__all__ = ["SQLiteCompiler"]


@compiler_extension
class SQLiteCompiler(compilers.SQLiteCompiler):
    def visit_LiteralTable(
        self,
        op: custom_operations.LiteralTable,
        *,
        data: tuple[tuple[Any, ...], ...],
        schema: ibis.Schema,
        name: str,
    ) -> sg.Select:
        # Note: SQLite does not support column aliases on VALUES in FROM.
        # A CTE column list is standard SQL and names the columns portably.
        values = custom_operations.LiteralTable.to_values(data)
        alias = sg.TableAlias(
            this=sg.to_identifier(name),
            columns=[sg.to_identifier(column, quoted=True) for column in schema],
        )
        source = sg.CTE(this=sg.values(values), alias=alias)
        query = sg.select("*", copy=False).from_(name, copy=False)
        query.set("with_", sg.With(expressions=[source]))
        return query
