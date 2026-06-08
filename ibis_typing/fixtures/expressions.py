"""Test fixtures for unit-testing Expression implementations."""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from contextlib import contextmanager

import ibis
import pytest
from attrs import frozen

from ibis_typing.checksum_buckets import IncrementalExpression

from .. import (
    Expression,
    IbisConnection,
    IbisSchema,
    IbisTable,
    evaluator,
    ibis_adapter,
)


@pytest.fixture
def evaluate_table(ibis_connection: IbisConnection) -> EvaluateTable:
    return EvaluateTable(ibis_connection)


@pytest.fixture
def fetch_table(ibis_connection: IbisConnection) -> FetchTable:
    return FetchTable(ibis_connection)


@pytest.fixture
def evaluate_expr(ibis_connection: IbisConnection) -> EvaluateExpr:
    return EvaluateExpr(ibis_connection)


@frozen
class EvaluateTable:
    ibis_connection: IbisConnection

    def __call__[E: Expression](
        self,
        target_table: type[E],
        rows: Iterable[IbisSchema],
        *,
        empty_tables: Iterable[type[IbisSchema]] = (),
    ) -> tuple[list[E], list[E]]:
        rows = list(rows)
        inputs = (row for row in rows if not isinstance(row, target_table))
        outputs = (row for row in rows if isinstance(row, target_table))
        expected = sorted(outputs, key=str)

        in_tables = ibis_adapter.tables_of_rows(inputs, empty_tables=empty_tables)
        with checked_incremental_cache() as cache:
            table = evaluator.from_expression(
                target_table, *in_tables.values(), cache=cache
            )

        fetch_table = FetchTable(self.ibis_connection)
        actual = fetch_table(table)

        return actual, expected


@contextmanager
def checked_incremental_cache() -> Iterator[dict]:
    cache = {}
    yield cache
    for expr, table in cache.items():
        if issubclass(expr, IncrementalExpression):
            evaluator.check_increment(table)


@frozen
class FetchTable:
    ibis_connection: IbisConnection

    def __call__[T: IbisSchema](self, ibis_table: IbisTable[T]) -> list[T]:
        return sorted(self.ibis_connection.fetch_table(ibis_table), key=str)


@frozen
class EvaluateExpr:
    ibis_connection: IbisConnection

    def __call__[V](self, expr: ibis.Expr, type_: type[V] | None = None) -> V:
        return self.ibis_connection.evaluate(expr, type_)
