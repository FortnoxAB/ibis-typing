"""Table providers for constructing `Expression` tables."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import Protocol, cast, overload

import ibis
from attrs import frozen

from .ibis_adapter import IbisDbSchema, IbisSchema, IbisTable, tables_of_rows


class TableProvider(Protocol):
    def __call__[S: IbisSchema](self, schema: type[S]) -> IbisTable[S] | None: ...


class RobustTableProvider(TableProvider, Protocol):
    def __call__[S: IbisSchema](self, schema: type[S]) -> IbisTable[S]: ...


type TableProviders = Sequence[TableProvider]


def provider_from_rows(
    rows: Iterable[IbisSchema], *, empty_tables: Iterable[type[IbisSchema]] = ()
) -> TableProvider:
    """Create a TableProvider from python IbisSchema rows."""
    lookup = tables_of_rows(rows, empty_tables=empty_tables)
    return cast(TableProvider, lookup.get)


def chain_providers(*providers) -> TableProvider:
    """Merge a sequence of providers into a single TableProvider."""

    def find_provider[T: IbisSchema](schema: type[T]) -> IbisTable[T] | None:
        for provider in providers:
            if table := provider(schema):
                return table
        return None

    return find_provider


@frozen
class EmptyTableProvider(RobustTableProvider):
    """Provide an empty table without data."""

    def __call__[S: IbisSchema](self, schema: type[S]) -> IbisTable[S]:
        return schema.of_rows([])


@frozen
class AbstractTableProvider(RobustTableProvider):
    """Provide an abstract non-executable table without data."""

    def __call__[S: IbisSchema](self, schema: type[S]) -> IbisTable[S]:
        table = ibis.table(schema.table_schema)
        return schema.of(table)

    @classmethod
    def from_reference[T: IbisSchema](cls, table: IbisTable[T]) -> IbisTable[T]:
        return table.table_schema.of(ibis.table(table.table.schema()))


@frozen
class DbTableProvider(TableProvider):
    """Provide tables for IbisDbSchema."""

    @overload
    def __call__[S: IbisDbSchema](self, schema: type[S]) -> IbisTable[S]: ...
    @overload
    def __call__[S: IbisSchema](self, schema: type[S]) -> IbisTable[S] | None: ...

    def __call__(self, schema):
        if not issubclass(schema, IbisDbSchema):
            return None

        catalog, database = schema.table_namespace
        table = ibis.table(
            schema.table_schema,
            name=schema.table_name,
            catalog=catalog,
            database=database,
        )
        return schema.of(table)


get_abstract_table = AbstractTableProvider()
get_empty_table = EmptyTableProvider()
get_db_table = DbTableProvider()


@frozen
class FilteredTableProvider(TableProvider):
    """Filter provided table by inclusion and exclusion list."""

    table_providers: TableProviders

    include: Sequence[type[IbisSchema]] | None = None
    exclude: Sequence[type[IbisSchema]] | None = None

    def __call__(self, schema):
        if self.exclude and issubclass(schema, tuple(self.exclude)):
            return None

        if self.include and not issubclass(schema, tuple(self.include)):
            return None

        provider = chain_providers(*self.table_providers)
        return provider(schema)
