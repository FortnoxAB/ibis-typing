"""Adapters with additional type support for `ibis.Table` expressions."""

from __future__ import annotations

import logging
import random
from collections.abc import Iterable, Mapping, MutableMapping
from typing import ClassVar, Self, cast, get_type_hints

import attrs
import ibis
from attrs import frozen
from ibis import literal

from . import ibis_types as it
from . import utils

logger = logging.getLogger(__name__)

# Export the deferred value for use in table expressions with ibis-typing tool support.
this = cast(ibis.Table, ibis._)


@frozen
class IbisSchema:
    """Type schema for `ibis.Table` expressions with extra tool support."""

    @classmethod
    def _get_table_schema(cls) -> Mapping[str, str]:
        """Default implementation of table_schema. Can be overridden."""
        type_hints = get_type_hints(cls)
        fields = attrs.fields(cls)
        return {
            field.name: str(it.to_ibis_core_type(type_hints[field.name]))
            for field in fields
        }

    @classmethod
    def _get_cols(cls) -> Self:
        """Typed column name access for `ibis.Table` expressions."""
        fields = (field.name for field in attrs.fields(cls))
        cols = utils.BoxedDict(dict(zip(fields, cls.table_schema)))
        return cast(Self, cols)

    table_schema: ClassVar[Mapping[str, str]] = utils.classproperty(_get_table_schema)
    cols: ClassVar[Self] = utils.classproperty(_get_cols)

    @classmethod
    def of[S: IbisSchema](cls: type[S], table: ibis.Table) -> IbisTable[S]:
        """Construct `IbisTable` from `ibis.Table` expression."""
        return IbisTable(table=table, table_schema=cls)

    @classmethod
    def of_rows[S: IbisSchema](cls: type[S], rows: Iterable[S]) -> IbisTable[S]:
        rows = list(rows)
        if not rows:
            # Some backends are unhappy about tables without rows.
            # Filter out a null row to make them happy.
            table = cls.of_rows([cls(*(None for _ in attrs.fields(cls)))]).table.filter(
                literal(False)
            )
            return cls.of(table)

        # Use local import to simplify import ordering in ibis_typing.__init__ facade.
        # This allows convenient creation of tables without explicitly using ibis_pyarrow.
        from .ibis_pyarrow import LiteralTableFromRows

        table = rows @ LiteralTableFromRows()
        return cls.of(table)


class IbisDbSchema(IbisSchema):
    """Type schema for `ibis.Table` expressions backed by a database table."""

    table_name: ClassVar[str]
    table_namespace: ClassVar[tuple[str, str]]


@frozen
class IbisTable[S: IbisSchema]:
    """Wrapper for Ibis table expressions with schema type information."""

    table: ibis.Table
    table_schema: type[S]

    @property
    def cols(self) -> S:
        """Typed column name access for `ibis.Table` expressions."""
        return self.table_schema.cols


type TableMap[S: IbisSchema] = MutableMapping[type[S], IbisTable[S]]


def tables_of_rows[S: IbisSchema](
    rows: Iterable[S],
    *,
    empty_tables: Iterable[type[S]] = (),
) -> TableMap[S]:
    # Introduce randomness to avoid relying on the order of the rows
    # which depends on backend
    row_list = list(rows)
    random.shuffle(row_list)

    rows_by_schema = utils.group_by_type(row_list)
    rows_by_schema.update({schema: [] for schema in empty_tables})

    return {schema: schema.of_rows(rows) for schema, rows in rows_by_schema.items()}
