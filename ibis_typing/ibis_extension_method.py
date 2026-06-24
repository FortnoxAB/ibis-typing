"""Implements infix typed ibis table operators, "extension methods", for flow syntax."""

from __future__ import annotations

import abc
from collections.abc import Sequence

from attrs import frozen
from ibis import Table, Value

from .expression import GenericExpression, SingleInputTableExpression, TableExpression
from .extension_method import ExtensionMethod
from .ibis_adapter import IbisSchema, IbisTable


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


class ValueMethod[T: Value, R: Value](ExtensionMethod[T, R], abc.ABC):
    """Apply operation to Value on left-hand side of this operator."""

    @abc.abstractmethod
    def apply(self, value: T) -> R: ...

    def __rmatmul__(self, other: T) -> R:
        return self.apply(other)


class SelfMethod[T: Value](ValueMethod[T, T], abc.ABC):
    pass


@frozen(init=False)
class ArgsMethod[T: Value](SelfMethod[T], abc.ABC):
    args: Sequence[T]

    def __init__(self, *args: T):
        self.__attrs_init__(args)  # type: ignore


class ExpressionMethod[S: IbisSchema, E: GenericExpression](
    ExtensionMethod[type[S], type[E]], abc.ABC
):
    """Extension method for chaining Expression class transforms."""

    @abc.abstractmethod
    def apply(self, schema: type[S]) -> TableExpression: ...

    def __rmatmul__(self, other: type[S]) -> type[E]:
        return self.apply(other).as_expression_schema()
