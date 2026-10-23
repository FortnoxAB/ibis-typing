from __future__ import annotations

import abc
from typing import Any, cast, override

import ibis
from attrs import frozen
from ibis.expr import datatypes as dt

from . import ibis_types as it
from .expression import GenericExpression, SingleInputTableExpression
from .ibis_adapter import IbisSchema, IbisTable
from .ibis_extension_method import ExpressionMethod

_ = it  # Needed for doctests


@frozen
class RevertibleTableExpression[S: IbisSchema](SingleInputTableExpression[S], abc.ABC):
    """Expressions which can be reverted and chained.

    >>> from ibis_typing import dt, IbisSchema, this

    >>> @frozen
    ... class IntSchema(IbisSchema):
    ...     value: it.Int64 = None

    >>> @frozen
    ... class FloatRevertible(RevertibleTableExpression):
    ...     col: it.NameOrType
    ...
    ...     def __call__(self, origin: IbisTable):
    ...         return origin.table.cast({self.col: dt.Float64})
    ...
    ...     def revert_call(self, table: IbisTable):
    ...         return table.table.cast({self.col: self.origin.table_schema[self.col]})

    >>> @frozen
    ... class StringRevertible(RevertibleTableExpression):
    ...     col: it.NameOrType
    ...
    ...     def __call__(self, origin: IbisTable):
    ...         return origin.table.cast({self.col: dt.String})
    ...
    ...     def revert_call(self, table: IbisTable):
    ...         return table.table.cast({self.col: self.origin.table_schema[self.col]})

    >>> int_table = IntSchema.of_rows([])
    >>> float_table = (
    ...     FloatRevertible(IntSchema, "value")
    ...     .as_expression_schema()
    ...     .from_expression(int_table)
    ... )
    >>> str_table = (
    ...     StringRevertible(float_table.table_schema, "value")
    ...     .as_expression_schema()
    ...     .from_expression(float_table)
    ... )
    >>> reverted_table = revert_all(str_table)

    >>> int_table.table_schema == IntSchema
    True
    >>> reverted_table.table_schema == IntSchema
    True
    """

    def revert_expression(self, transformed: IbisTable[IbisSchema]) -> IbisTable[S]:
        table = self.revert_call(transformed)
        return self.origin.of(table)

    @abc.abstractmethod
    def __call__(self, origin: IbisTable[S]) -> ibis.Table: ...

    @abc.abstractmethod
    def revert_call(self, transformed: IbisTable[IbisSchema]) -> ibis.Table: ...


def revert_all(table: IbisTable[IbisSchema]) -> IbisTable[IbisSchema]:
    """Revert all revertible expressions in the chain."""
    while issubclass((schema := table.table_schema), GenericExpression) and isinstance(
        constructor := schema.get_table_expression(), RevertibleTableExpression
    ):
        # Narrowing a generic class leaves its schema type argument unknown.
        revertible = cast(RevertibleTableExpression[IbisSchema], constructor)
        table = revertible.revert_expression(table)

    return table


@frozen
class AsRevertible[E: ExpressionExport[AsRevertible[Any]]](
    ExpressionMethod[IbisSchema, GenericExpression]
):
    """Wrap any non-parametric ExpressionExport as an ExpressionMethod.

    For any parametric ExpressionExport, implement a parametric ExpressionMethod instead."""

    revertible: type[E]

    @override
    def apply(self, schema: type[IbisSchema]) -> ExpressionExport[AsRevertible[Any]]:
        # Upcast to specialize the `method` parameter of the constructor.
        revertible: type[ExpressionExport[AsRevertible[Any]]] = self.revertible
        return revertible(schema, self)


@frozen
class ExpressionExport[R: ExpressionMethod[Any, Any]](
    RevertibleTableExpression[IbisSchema]
):
    """Basic revertible transform, composable with `Schema @ AsRevertible(ExportExpression)`.

    All parameters except for origin schema is kept in the ExpressionMethod.
    The ExpressionMethod is then passed to the ExpressionExport.
    """

    method: R

    @override
    def __call__(self, origin: IbisTable[IbisSchema]) -> ibis.Table:
        return origin.table

    @override
    def revert_call(self, transformed: IbisTable[IbisSchema]) -> ibis.Table:
        return transformed.table

    @property
    @override
    def generated_class_name(self) -> str:
        return self.origin.__name__


class UUIDToStringExport(ExpressionExport[AsRevertible[Any]]):
    """Cast UUID to strings for e.g. Apache Hive compatibility.

    See
    https://hive.apache.org/docs/latest/language/languagemanual-types/
    """

    @override
    def __call__(self, origin: IbisTable[IbisSchema]) -> ibis.Table:
        return origin.table.cast(dict.fromkeys(self._get_uuid_casts(), dt.string))

    @override
    def revert_call(self, transformed: IbisTable[IbisSchema]) -> ibis.Table:
        return transformed.table.cast(dict.fromkeys(self._get_uuid_casts(), dt.uuid))

    def _get_uuid_casts(self):
        schema = ibis.schema(self.origin.table_schema)
        return [column for column, type_ in schema.items() if type_ == dt.uuid]
