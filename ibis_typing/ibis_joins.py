"""Provides table join methods for `ibis.Table`.

Implements key-column-based join methods for tables,
with de-duplication of key columns by default.
"""

# ruff: noqa: RUF002  # Non-ascii `Unicode characters
from __future__ import annotations

from collections.abc import Iterable, Sequence
from enum import StrEnum
from typing import ClassVar

import attrs
import ibis
import more_itertools
from attrs import frozen
from ibis import Table

from ibis_typing import ibis_types as it
from ibis_typing import this
from ibis_typing.ibis_extension_method import TableMethod

__all__ = [
    "AntiJoin",
    "InnerJoin",
    "JoinMethod",
    "LeftJoin",
    "OuterJoin",
    "OuterJoinParallel",
    "anti_join",
    "inner_join",
    "join",
    "left_join",
    "outer_join",
    "outer_join_parallel",
]


class JoinMethod(StrEnum):
    """Existing `ibis.Table` join methods."""

    INNER = "inner"
    LEFT = "left"
    OUTER = "outer"
    SEMI = "semi"
    ANTI = "anti"
    ANY_INNER = "any_inner"
    ANY_LEFT = "any_left"


@frozen(init=False)  # Keep signature of ExtensionMethod identical to ordinary function
class Join(TableMethod):
    tables: Sequence[Table]
    keys: Iterable[it.NameOrType]

    arbitrary: Iterable[it.NameOrType] = ()
    max: Iterable[it.NameOrType] = ()
    min: Iterable[it.NameOrType] = ()

    how: JoinMethod | None = None

    _how: ClassVar[JoinMethod]

    def apply(self, table):
        kwargs = attrs.asdict(self)
        tables = kwargs.pop("tables")
        return join(table, *tables, **kwargs)

    def __init__(
        self,
        *tables: Table,
        keys: Iterable[it.NameOrType],
        arbitrary: Iterable[it.NameOrType] = (),
        max: Iterable[it.NameOrType] = (),
        min: Iterable[it.NameOrType] = (),
        how: JoinMethod | None = None,
    ):
        self.__attrs_init__(tables, keys, arbitrary, max, min, how or self._how)


class LeftJoin(Join):
    _how = JoinMethod.LEFT


class InnerJoin(Join):
    _how = JoinMethod.INNER


class OuterJoin(Join):
    _how = JoinMethod.OUTER


class OuterJoinParallel(Join):
    _how = JoinMethod.OUTER

    def apply(self, table):
        kwargs = attrs.asdict(self)
        kwargs.pop("how")
        tables = kwargs.pop("tables")
        return outer_join_parallel(table, *tables, **kwargs)


class AntiJoin(Join):
    _how = JoinMethod.ANTI


def join(
    *tables: Table,
    how: JoinMethod,
    keys: Iterable[it.NameOrType],
    arbitrary: Iterable[it.NameOrType] = (),
    max: Iterable[it.NameOrType] = (),
    min: Iterable[it.NameOrType] = (),
) -> Table:
    """Join tables depth-first 𝒪(n) without duplicated columns for keys."""
    left, *rights = tables
    if not rights:
        return left
    right, *tail = rights

    join_method = getattr(left, f"{how}_join")

    joined: Table = join_method(right, keys, rname="{name}_right")

    # Note: Keys will exist in the original left column name, without "_right" suffix,
    # when doing left joins.
    # For outer joins, the key might be from either table.
    arbitrary = (*keys, *arbitrary) if how == JoinMethod.OUTER else arbitrary
    post_join_ops = {
        str(col): op(this[col], this[right])
        for op, cols in [
            (ibis.coalesce, arbitrary),
            (ibis.greatest, max),
            (ibis.least, min),
        ]
        for col in cols
        if (right := f"{col}_right") in joined.columns
    }
    # drops can be precomputed before mutate: mutate() preserves column names
    drops = [
        right
        for col in (*keys, *post_join_ops)
        if (right := f"{col}_right") in joined.columns
    ]
    table = joined.mutate(**post_join_ops).drop(*drops)

    return join(
        table,
        *tail,
        how=how,
        keys=keys,
        arbitrary=arbitrary,
        max=max,
        min=min,
    )


def outer_join_parallel(
    *tables: Table,
    keys: Iterable[it.NameOrType],
    arbitrary: Iterable[it.NameOrType] = (),
    max: Iterable[it.NameOrType] = (),
    min: Iterable[it.NameOrType] = (),
) -> Table:
    """Join tables breadth-first 𝒪(log n) without duplicated columns for keys."""
    if len(tables) == 1:
        return tables[0]

    table_pairs = more_itertools.chunked(tables, n=2)
    joined = [
        join(
            *pair,
            how=JoinMethod.OUTER,
            keys=keys,
            arbitrary=arbitrary,
            max=max,
            min=min,
        )
        for pair in table_pairs
    ]

    return outer_join_parallel(
        *joined,
        keys=keys,
        arbitrary=arbitrary,
        max=max,
        min=min,
    )


def left_join(
    *tables: Table,
    keys: Iterable[it.NameOrType],
    arbitrary: Iterable[it.NameOrType] = (),
    max: Iterable[it.NameOrType] = (),
    min: Iterable[it.NameOrType] = (),
) -> Table:
    table, *tail = tables
    return table @ LeftJoin(*tail, keys=keys, arbitrary=arbitrary, max=max, min=min)


def inner_join(
    *tables: Table,
    keys: Iterable[it.NameOrType],
    arbitrary: Iterable[it.NameOrType] = (),
    max: Iterable[it.NameOrType] = (),
    min: Iterable[it.NameOrType] = (),
) -> Table:
    table, *tail = tables
    return table @ InnerJoin(*tail, keys=keys, arbitrary=arbitrary, max=max, min=min)


def outer_join(
    *tables: Table,
    keys: Iterable[it.NameOrType],
    arbitrary: Iterable[it.NameOrType] = (),
    max: Iterable[it.NameOrType] = (),
    min: Iterable[it.NameOrType] = (),
) -> Table:
    table, *tail = tables
    return table @ OuterJoin(*tail, keys=keys, arbitrary=arbitrary, max=max, min=min)


def anti_join(
    *tables: Table,
    keys: Iterable[it.NameOrType],
    arbitrary: Iterable[it.NameOrType] = (),
    max: Iterable[it.NameOrType] = (),
    min: Iterable[it.NameOrType] = (),
) -> Table:
    table, *tail = tables
    return table @ AntiJoin(*tail, keys=keys, arbitrary=arbitrary, max=max, min=min)
