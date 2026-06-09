from attrs import frozen
from ibis import literal

from ibis_typing import Expression, IbisTable, ibis_utils, it, this
from ibis_typing.ibis_utils import Aggregate
from ibis_typing.partitioning import (
    ByNumberOfBuckets,
    BySize,
    PartitionColumns,
)
from tests.conftest import SimpleSchema


def test_by_size_partition_policy():
    policy = BySize(2)
    actual = policy.partitions(["1", "2", "3", "4", "5"])
    expected = [["1", "2"], ["3", "4"], ["5"]]
    assert actual == expected


def test_by_buckets_partition_policy():
    policy = ByNumberOfBuckets(2)
    actual = policy.partitions(["1", "2", "3", "4", "5"])
    expected = [["1", "2", "3"], ["4", "5"]]
    assert actual == expected


def test_partition_columns_creates_correct_partitions(fetch_table):
    rows = [
        SimpleSchema(id=0, value=2),
        SimpleSchema(id=1, value=3),
    ]
    expected = [
        SimpleSchema(id=0, value=2),
        SimpleSchema(id=1, value=3),
    ]

    table = SimpleSchema.of_rows(rows).table
    table = table.mutate(**{"de_partitioned_value": literal(0)})
    table, _ = ibis_utils.partition_columns(
        table, keys=[SimpleSchema.cols.id], partition_policy=BySize(1)
    )

    actual = fetch_table(SimpleSchema.of(table))

    assert actual == expected


def test_PartitionedColumns_preserves_schema(evaluate_table):
    @frozen
    class Transform(SimpleSchema, Expression):
        const: it.Int64

        @classmethod
        def from_expression(cls, inputs: IbisTable[SimpleSchema]):
            cols = inputs.cols

            table = inputs.table @ Aggregate(
                by=[cols.id],
                expr={
                    cols.value: this[cols.value].max(),
                    "const": literal(1),
                },
            )

            return cls.of(table)

    spec = PartitionColumns(keys=(SimpleSchema.cols.id,), partition_policy=BySize(1))
    PartitionedTransform = spec.partition(Transform)

    rows = [
        SimpleSchema(id=0, value=0),
        SimpleSchema(id=0, value=2),
        SimpleSchema(id=1, value=1),
        SimpleSchema(id=1, value=3),
    ]
    expected = [
        Transform(id=0, value=2, const=1),
        Transform(id=1, value=3, const=1),
    ]

    actual, _ = evaluate_table(PartitionedTransform, rows)
    assert actual == expected
