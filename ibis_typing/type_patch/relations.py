"""Fix type hinting of `ibis_table.table[ibis_table.cols.name]` operation.

Add signature overloading for use with `IbisTable.cols` column names.
Indexing an `ibis.ir.Table` with an `IbisSchema` column reference
now returns a value typed `ibis.ir.Column` instance,
enabling tools to figure out what operations are available on the columns.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping, Sequence
from typing import TYPE_CHECKING, Any, Literal, overload

from ibis import Table, ir
from ibis import selectors as s
from ibis.common.selectors import Selector
from ibis.expr.schema import SchemaLike

from .patchers import MethodOverloadPatcher, TypeCheckingModulePatcher


def get_patchers():
    methods = [
        TableExtensionMethodPatch,
        TableAggregate,
        TableCast,
        TableDistinct,
        TableDrop,
        TableDropNull,
        TableFillNull,
        TableGetItem,
        TableOrderBy,
        TableRelocate,
        TableRename,
        TableSelect,
    ]
    return [
        TypeCheckingModulePatcher(__file__),
        *[MethodOverloadPatcher(patch) for patch in methods],
    ]


class TableExtensionMethodPatch(Table):
    # Type `table @ it.deferred.method()`, where `it.deferred` is typed as a Table.
    # Returns NotImplemented to defer to `other.__rmatmul__` at runtime.
    def __matmul__(self, other: Table) -> Table:
        return NotImplemented


class TableGetItem(Table):
    # A field's `None` selects no column (scheduling.ibis.type_patch).
    @overload
    def __getitem__(self, col: None) -> NoReturn: ...

    # Type annotations for IntelliJ (treats Union types differently from type checkers)
    # Primitives
    @overload
    def __getitem__(self, col: it.BooleanType) -> ir.BooleanColumn: ...
    @overload
    def __getitem__(self, col: it.IntegerType) -> ir.IntegerColumn: ...
    @overload
    def __getitem__(self, col: it.FloatingType) -> ir.FloatingColumn: ...
    @overload
    def __getitem__(self, col: it.BinaryType) -> ir.BinaryColumn: ...
    @overload
    def __getitem__(self, col: it.StringType) -> ir.StringColumn: ...
    # Complex types
    @overload
    def __getitem__(self, col: it.TimestampType) -> ir.TimestampColumn: ...
    @overload
    def __getitem__(self, col: it.DateType) -> ir.DateColumn: ...
    @overload
    def __getitem__(self, col: it.TimeType) -> ir.TimeColumn: ...
    @overload
    def __getitem__(self, col: it.DecimalType) -> ir.DecimalColumn: ...
    @overload
    def __getitem__(self, col: it.UUIDType) -> ir.UUIDColumn: ...
    # Non-typed collections
    @overload
    def __getitem__(self, col: it.StructType) -> ir.StructColumn: ...
    # Collections
    @overload
    def __getitem__(self, col: it.ArrayType[Any]) -> ir.ArrayColumn: ...
    @overload
    def __getitem__(self, col: it.MapType[Any, Any]) -> ir.MapColumn: ...
    @overload
    def __getitem__(self, col: it.JSONType) -> ir.JSONColumn: ...

    # Type annotations for type checker
    # Primitives
    @overload
    def __getitem__(self, col: it.Boolean) -> ir.BooleanColumn: ...
    @overload
    def __getitem__(self, col: it.Integer) -> ir.IntegerColumn: ...
    @overload
    def __getitem__(self, col: it.Floating) -> ir.FloatingColumn: ...
    @overload
    def __getitem__(self, col: it.Binary) -> ir.BinaryColumn: ...
    @overload
    def __getitem__(self, col: it.String) -> ir.StringColumn: ...
    # Complex types
    @overload
    def __getitem__(self, col: it.Timestamp) -> ir.TimestampColumn: ...
    @overload
    def __getitem__(self, col: it.Date) -> ir.DateColumn: ...
    @overload
    def __getitem__(self, col: it.Time) -> ir.TimeColumn: ...
    @overload
    def __getitem__(self, col: it.Decimal) -> ir.DecimalColumn: ...
    @overload
    def __getitem__(self, col: it.UUID) -> ir.UUIDColumn: ...
    # Collections
    @overload
    def __getitem__(self, col: it.Struct[Any]) -> ir.StructColumn: ...
    @overload
    def __getitem__(self, col: it.Map[Any, Any]) -> ir.MapColumn: ...
    @overload
    def __getitem__(self, col: it.Array[Any]) -> ir.ArrayColumn: ...
    @overload
    def __getitem__(self, col: it.JSON) -> ir.JSONColumn: ...

    # Unresolved types
    @overload
    def __getitem__(self, col: Any) -> ir.Column: ...

    def __getitem__(self, col: Any) -> ir.Column:
        raise NotImplementedError


class TableAggregate(Table):
    @overload
    def aggregate(
        self,
        metrics: Iterable[Any] = (),
        /,
        *,
        by: Sequence[Any] = (),
        having: Sequence[Any] = (),
        **kwargs: ir.Value,
    ) -> Table: ...

    @overload
    def aggregate(
        self,
        metrics: Sequence[it.NameOrTypeOrValue] = (),
        /,
        *,
        by: Sequence[it.NameOrTypeOrValue] = (),
        having: Sequence[ir.BooleanValue] = (),
        **kwargs: ir.Value,
    ) -> Table: ...

    def aggregate(
        self,
        metrics: Any = (),
        /,
        *,
        by: Any = (),
        having: Any = (),
        **kwargs: ir.Value,
    ) -> Table:
        raise NotImplementedError


class TableSelect(Table):
    @overload
    def select(
        self,
        *exprs: ir.Value | str | Iterable[ir.Value | str],
        **named_exprs: ir.Value | str,
    ) -> Table: ...

    @overload
    def select(
        self,
        *exprs: it.NameOrTypeOrValue | Iterable[it.NameOrTypeOrValue],
        **named_exprs: it.NameOrTypeOrValue,
    ) -> Table: ...

    def select(
        self,
        *exprs: Any,
        **named_exprs: Any,
    ) -> Table:
        raise NotImplementedError


class TableCast(Table):
    @overload
    def cast(self, schema: SchemaLike) -> Table: ...
    @overload
    def cast(self, schema: Mapping[it.NameOrType, Any]) -> Table: ...
    def cast(self, schema: Any) -> Table:
        raise NotImplementedError


class TableDistinct(Table):
    @overload
    def distinct(
        self,
        *,
        on: it.NameOrType | Iterable[it.NameOrType] | None = None,
        keep: Literal["first", "last"] | None = "first",
    ) -> Table: ...
    @overload
    def distinct(
        self,
        *,
        on: s.Selector = None,
        keep: Literal["first", "last"] | None = "first",
    ) -> Table: ...
    def distinct(
        self,
        *,
        on: Any = None,
        keep: Literal["first", "last"] | None = "first",
    ) -> Table:
        raise NotImplementedError


class TableDrop(Table):
    @overload
    def drop(self, *fields: str | Selector) -> Table: ...
    @overload
    def drop(self, *fields: it.NameOrType | Selector) -> Table: ...

    def drop(self, *fields: Any) -> Table:
        raise NotImplementedError


class TableDropNull(Table):
    @overload
    def drop_null(
        self,
        subset: Sequence[it.NameOrType] | it.NameOrType | None = None,
        /,
        *,
        how: Literal["any", "all"] = "any",
    ) -> Table: ...
    @overload
    def drop_null(self, subset: Any = None, /, *, how: str = "any") -> Table: ...

    def drop_null(self, subset: Any = None, /, *, how: str = "any") -> Table:
        raise NotImplementedError


class TableFillNull(Table):
    @overload
    def fill_null(self, replacements: ir.Scalar, /) -> Table: ...
    @overload
    def fill_null(self, replacements: Mapping[it.NameOrType, Any], /) -> Table: ...

    def fill_null(self, replacements: Any, /) -> Table:
        raise NotImplementedError


class TableOrderBy(Table):
    @overload
    def order_by(
        self,
        *by: str
        | ir.Column
        | Selector
        | Sequence[str]
        | Sequence[ir.Column]
        | Sequence[Selector]
        | None,
    ) -> Table: ...
    @overload
    def order_by(self, *by: it.NameOrTypeOrValue | Selector) -> Table: ...

    def order_by(self, *by: Any) -> Table:
        raise NotImplementedError


class TableRename(Table):
    @overload
    def rename(
        self,
        method: Mapping[it.NameOrType, it.NameOrType] | None = None,
        /,
        **substitutions: it.NameOrType,
    ) -> Table: ...

    @overload
    def rename(
        self,
        method: (
            str
            | Callable[[str], str | None]
            | Literal["snake_case", "ALL_CAPS"]
            | Mapping[str, str]
            | None
        ) = None,
        /,
        **substitutions: str,
    ) -> Table: ...

    def rename(self, method: Any = None, /, **substitutions: Any) -> Table:
        raise NotImplementedError


class TableRelocate(Table):
    @overload
    def relocate(
        self,
        *columns: it.NameOrType,
        before: it.NameOrType | None = None,
        after: it.NameOrType | None = None,
        **kwargs: it.NameOrType,
    ) -> Table: ...

    @overload
    def relocate(
        self,
        *columns: str | s.Selector,
        before: str | s.Selector | None = None,
        after: str | s.Selector | None = None,
        **kwargs: str,
    ) -> Table: ...

    def relocate(
        self,
        *columns: Any,
        before: Any | None = None,
        after: Any | None = None,
        **kwargs: Any,
    ) -> Table:
        raise NotImplementedError


if TYPE_CHECKING:
    from typing import NoReturn

    from ibis_typing import ibis_types as it
