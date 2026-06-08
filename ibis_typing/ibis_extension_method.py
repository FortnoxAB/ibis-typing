"""Implements infix typed ibis table operators, "extension methods", for flow syntax."""

from __future__ import annotations

import abc
from typing import cast

from attrs import frozen
from ibis import Table, Value

from ibis_typing.expression import GenericExpression, SingleInputTableExpression
from ibis_typing.extension_method import Deferred, ExtensionMethod
from ibis_typing.ibis_adapter import IbisSchema, IbisTable

# Typed token for chaining instance methods after extension methods.
deferred = cast(Table, Deferred())
defer_val = cast(Value, Deferred())


@frozen
class TableMethod(ExtensionMethod[Table, Table], abc.ABC):
    """Apply operation to Table on left-hand side of this operator."""

    @abc.abstractmethod
    def apply(self, table: Table) -> Table: ...

    def __rmatmul__(self, other):
        return self.apply(other)

    def as_expression_schema(
        self: TableMethod, origin: type[IbisSchema], /, preserves_schema: bool = False
    ) -> type[GenericExpression]:
        return TableMethodExpression(
            origin, self, preserves_schema
        ).as_expression_schema()


@frozen
class TableMethodExpression(SingleInputTableExpression):
    method: TableMethod
    preserves_schema: bool = False

    @property
    def output_schema(self):
        if not self.preserves_schema:
            return None
        return self.origin

    def __call__(self, origin: IbisTable) -> Table:
        return origin.table @ self.method


@frozen
class ValueMethod[T: Value, R: Value](ExtensionMethod[T, R], abc.ABC):
    """Apply operation to Value on left-hand side of this operator."""

    @abc.abstractmethod
    def apply(self, value: T) -> R: ...

    def __rmatmul__(self, other: T) -> R:
        return self.apply(other)
