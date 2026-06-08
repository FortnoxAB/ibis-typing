r"""Provides typed `ibis.Table` operations.

Collects library functions for writing typed `ibis.Table` expressions.

Regex for migrating from function calls to infix operator calls follows.

ibis_utils\.aggregate\(\s*([^,]+),
$1 @ Aggregate(
ibis_utils\.select\(\s*([^,]+),
$1 @ Select(

ibis_utils\.left_join\(\s*([^,]+),
$1 @ LeftJoin(
ibis_utils\.inner_join\(\s*([^,]+),
$1 @ InnerJoin(
ibis_utils\.outer_join\(\s*([^,]+),
$1 @ OuterJoin(
ibis_utils\.outer_join_parallel\(\s*([^,]+),
$1 @ OuterJoinParallel(
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from typing import cast, overload

import attrs
from attrs import frozen
from ibis import Table, Value

from ibis_typing.ibis_extension_method import TableMethod

from . import ibis_types as it
from . import this
from .ibis_adapter import TableMap, tables_of_rows
from .ibis_defaults import (
    fill_nulls,
    numeric_default_provider,
    numeric_or_bool_default_provider,
)
from .ibis_joins import (
    AntiJoin,
    InnerJoin,
    JoinMethod,
    LeftJoin,
    OuterJoin,
    OuterJoinParallel,
    anti_join,
    inner_join,
    join,
    left_join,
    outer_join,
    outer_join_parallel,
)
from .partitioning import (
    ByNumberOfBuckets,
    BySize,
    PartitionPolicy,
    partition_columns,
)

__all__ = [
    "Aggregate",
    "AntiJoin",
    "ByNumberOfBuckets",
    "BySize",
    "InnerJoin",
    "JoinMethod",
    "LeftJoin",
    "OuterJoin",
    "OuterJoinParallel",
    "PartitionPolicy",
    "Select",
    "TableMap",
    "aggregate",
    "anti_join",
    "fill_nulls",
    "inner_join",
    "join",
    "left_join",
    "numeric_default_provider",
    "numeric_or_bool_default_provider",
    "outer_join",
    "outer_join_parallel",
    "partition_columns",
    "select",
    "tables_of_rows",
]


@frozen(init=False)
class Select(TableMethod):
    names: Sequence[it.NameOrType]
    expr: Mapping[it.NameOrType, Value] | None = None
    drop: Sequence[it.NameOrType] = ()

    def apply(self, table):
        kwargs = attrs.asdict(self)
        names = kwargs.pop("names")
        drop = kwargs.pop("drop")
        table = select(table, *names, **kwargs)
        if drop:
            table = table.drop(self.drop)
        return table

    def __init__(
        self,
        *names: it.NameOrType,
        expr: Mapping[it.NameOrType, Value] | None = None,
        drop: Sequence[it.NameOrType] = (),
    ):
        self.__attrs_init__(names, expr, drop)  # type: ignore


@frozen(kw_only=True)
class Aggregate(TableMethod):
    by: Iterable[it.NameOrType]
    expr: Mapping[it.NameOrType, Value] | None = None
    arbitrary: Iterable[it.NameOrType] = ()
    sum: Iterable[it.NameOrType] = ()
    min: Iterable[it.NameOrType] = ()
    max: Iterable[it.NameOrType] = ()

    def apply(self, table):
        kwargs = attrs.asdict(self)
        return aggregate(table, **kwargs)


def aggregate(  # noqa: PLR0913 # Too many arguments in function definition (6 > 5)
    table: Table,
    /,
    by: Iterable[it.NameOrType],
    expr: Mapping[it.NameOrType, Value] | None = None,
    arbitrary: Iterable[it.NameOrType] = (),
    sum: Iterable[it.NameOrType] = (),
    min: Iterable[it.NameOrType] = (),
    max: Iterable[it.NameOrType] = (),
) -> Table:
    cols = table.columns
    expr = expr or {}
    exprs = {
        **{col: this[col].arbitrary() for col in arbitrary},
        **{col: this[cast(it.Floating, col)].sum() for col in sum},
        **{col: this[col].min() for col in min},
        **{col: this[col].max() for col in max},
        **expr,
    }
    out_cols = exprs
    order = [
        *(col for col in cols if col in out_cols),
        *(col for col in exprs if col not in cols),
    ]
    values = {str(col): exprs[col] for col in order}
    return table.aggregate(by=by, **values)  # ty:ignore[no-matching-overload]


@overload
def select(
    table: Table,
    expr: Mapping[it.NameOrType, Value],
    /,
) -> Table: ...


@overload
def select(
    table: Table,
    *names: it.NameOrType,
    expr: Mapping[it.NameOrType, Value] | None = None,
) -> Table: ...


def select(
    table: Table,
    *names: it.NameOrType,
    expr: Mapping[it.NameOrType, Value] | None = None,
) -> Table:
    """Typed variant of `ibis.table.select()`.

    Preserve existing columns and add an expression.
    select(table, expr={"new_column": ibis.literal(1)})

    Select one existing column and add an expression.
    select(table, "existing_column", expr={"new_column": ibis.literal(1)})

    Drop existing columns and add an expression.
    select(table, {"new_column": ibis.literal(1)})
    """
    cols = table.columns
    # Allow the `names` argument to be the `expr` mapping if no names are to be selected.
    # This mirrors the default `ibis` API.
    if len(names) == 1 and isinstance(names[0], dict):
        expr = cast(Mapping, names[0])
        names = ()
    else:
        expr = expr or {}
        names = names or cols

    out_cols = dict.fromkeys((*names, *expr))
    order = [
        *(col for col in cols if col in out_cols),
        *(col for col in expr if col not in cols),
    ]
    values = {str(col): expr.get(col, this[col]) for col in order}
    return table.select(**values)
