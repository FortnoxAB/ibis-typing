"""Partition `ibis.Table` expressions by column for memory usage optimization."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable, Sequence

import more_itertools
from attrs import frozen
from ibis import Table

from ibis_typing.ibis_extension_method import TableMethod

from . import ibis_joins
from . import ibis_types as it
from .expression import GenericExpression, IdentityTableExpression
from .ibis_adapter import IbisSchema, IbisTable

__all__ = [
    "ByNumberOfBuckets",
    "BySize",
    "PartitionColumns",
    "PartitionPolicy",
    "partition_columns",
]


@frozen
class PartitionColumns(TableMethod):
    keys: Sequence[it.NameOrType]
    partition_policy: PartitionPolicy

    def apply(self, table: Table) -> Table:
        tables = partition_columns(
            table, keys=self.keys, partition_policy=self.partition_policy
        )
        return ibis_joins.outer_join_parallel(*tables, keys=self.keys)

    def partition(self, schema: type[IbisSchema]) -> type[GenericExpression]:
        return self.as_expression_schema(schema, preserves_schema=True)


@frozen
class PartitionedColumnTableExpression[S: IbisSchema](IdentityTableExpression[S]):
    params: PartitionColumns

    def __call__(self, origin: IbisTable[S]) -> Table:
        return origin.table @ self.params


def partition_columns(
    table: Table,
    *,
    keys: Iterable[it.NameOrType],
    partition_policy: PartitionPolicy,
) -> list[Table]:
    value_columns = [col for col in table.columns if col not in keys]
    return [
        table.select(*keys, *cols)
        for cols in partition_policy.partitions(value_columns)
    ]


type Partition = Sequence[it.NameOrType]


class PartitionPolicy(ABC):
    @abstractmethod
    def partitions(self, columns: Sequence[it.NameOrType]) -> list[Partition]: ...


@frozen
class BySize(PartitionPolicy):
    partition_size: int

    def partitions(self, columns: Sequence[it.NameOrType]) -> list[Partition]:
        return list(more_itertools.chunked(columns, self.partition_size))


@frozen
class ByNumberOfBuckets(PartitionPolicy):
    buckets: int

    def partitions(self, columns: Sequence[it.NameOrType]) -> list[Partition]:
        return [list(bucket) for bucket in more_itertools.divide(self.buckets, columns)]
