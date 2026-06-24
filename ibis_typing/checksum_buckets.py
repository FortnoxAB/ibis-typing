from __future__ import annotations

import abc
import functools
import operator
from collections.abc import Sequence
from typing import ClassVar

from attrs import frozen

from . import ibis_types as it
from .expression import (
    Expression,
    GenericExpression,
    TableExpression,
)
from .ibis_adapter import IbisSchema, IbisTable, this
from .ibis_deferred import deferred
from .ibis_extension_method import ExpressionMethod
from .ibis_joins import LeftJoin, OuterJoin
from .ibis_ops import ColumnChecksum
from .ibis_time import TimestampNow
from .ibis_utils import Aggregate

__all__ = [
    "AsBucketedInputs",
    "AsIncrementedBuckets",
    "BucketedInputsExpression",
    "BucketedInputsParams",
    "ChecksumBuckets",
    "ChecksumBucketsIncrementTableExpression",
    "ChecksumParams",
    "IncrementalExpression",
]


@frozen
class IncrementalParams:
    group_by: Sequence[it.NameOrType]
    updated_at_col: it.Timestamp = "checksum_updated_at"  # type: ignore


@frozen(kw_only=True)
class ChecksumParams(IncrementalParams):
    inputs: type[IbisSchema]
    checksum_col: it.Int64 = "checksum"  # type: ignore


@frozen(kw_only=True)
class BucketedInputsParams(IncrementalParams):
    buckets: type[ChecksumBuckets]


class IncrementalExpression(Expression, abc.ABC):
    """Expressions that can be updated incrementally."""

    incremental_params: ClassVar[IncrementalParams]


class BucketedInputsExpression(IncrementalExpression, abc.ABC):
    """Base class for implementing IncrementalExpressions.

    On incremental updates,
    the expression is only provided inputs from updated ChecksumBuckets.
    """

    incremental_params: ClassVar[BucketedInputsParams]

    @classmethod
    def get_parameter_schema_types(cls):
        # Replace plain IbisTable[Inputs] with IbisTable[BucketedInputs] variant.
        params = super().get_parameter_schema_types()
        buckets = cls.incremental_params.buckets
        inputs = buckets.incremental_params.inputs

        if inputs not in params.values():
            raise TypeError(f"{cls.__name__} lacks {ChecksumBuckets.__name__} input.")

        return {
            name: buckets @ AsBucketedInputs() if issubclass(schema, inputs) else schema
            for name, schema in params.items()
        }


@frozen
class ChecksumBucketsTableExpression(TableExpression):
    params: ChecksumParams

    @property
    def input_schemas(self):
        return {"inputs": self.params.inputs, "timestamp": TimestampNow}

    def __call__(self, inputs: IbisTable, timestamp: IbisTable[TimestampNow]):
        args = self.params
        checksums = [
            this[col_name] @ ColumnChecksum()
            for col_name in sorted(inputs.table.columns)
            if col_name not in args.group_by
        ]
        return (
            inputs.table
            @ Aggregate(
                by=args.group_by,
                expr={args.checksum_col: functools.reduce(operator.xor, checksums)},
            )
            @ deferred.join(timestamp.table)
            .rename({args.updated_at_col: timestamp.cols.timestamp})
            .relocate(args.updated_at_col, before=args.checksum_col)
        )


class ChecksumBuckets(IncrementalExpression, GenericExpression):
    """Checksum for inputs grouped by specific key columns."""

    incremental_params: ClassVar[ChecksumParams]  # constant

    @classmethod
    def get_table_expression(cls):
        return ChecksumBucketsTableExpression(cls.incremental_params)

    @classmethod
    def construct_increment[E: ChecksumBuckets](
        cls: type[E],
        buckets: IbisTable[E],
        prior: IbisTable[E],
        timestamp: IbisTable[TimestampNow],
    ) -> IbisTable[E]:
        """Calculate updated ChecksumBuckets table."""
        args = cls.incremental_params

        table = (
            buckets.table
            @ OuterJoin(prior.table, keys=args.group_by)
            @ deferred.fill_null({args.checksum_col: 0})
            .filter(
                ~this[args.checksum_col].identical_to(
                    this[f"{args.checksum_col}_right"]
                )
            )
            .join(timestamp.table)
            .rename({args.updated_at_col: timestamp.cols.timestamp})
            .relocate(args.updated_at_col, before=args.checksum_col)
            .select(buckets.table.columns)
        )

        return cls.of(table)


@frozen
class AsIncrementedBuckets(ExpressionMethod):
    target: type[IncrementalExpression]

    def apply(self, schema):
        return ChecksumBucketsIncrementTableExpression(schema, self.target)


@frozen
class AsBucketedInputs(ExpressionMethod):
    def apply(self, schema):
        return BucketedInputsTableExpression(schema)


@frozen
class ChecksumBucketsIncrementTableExpression(TableExpression):
    buckets: type[ChecksumBuckets]
    target: type[IncrementalExpression]

    @property
    def input_schemas(self):
        return {"buckets": self.buckets, "target": self.target}

    def __call__(self, buckets: IbisTable, target: IbisTable):
        target_updated_at = self.target.incremental_params.updated_at_col
        bucket_updated_at = self.buckets.incremental_params.updated_at_col

        is_updated = this[bucket_updated_at] > target.table[target_updated_at].max()

        return buckets.table.filter(is_updated)

    @property
    def generated_class_name(self) -> str:
        return f"{self.buckets.__name__}Increment"


@frozen
class BucketedInputsTableExpression(TableExpression):
    buckets: type[ChecksumBuckets]

    @property
    def input_schemas(self):
        inputs = self.buckets.incremental_params.inputs
        return {"buckets": self.buckets, "inputs": inputs}

    def __call__(self, buckets: IbisTable, inputs: IbisTable):
        args = self.buckets.incremental_params
        return (
            buckets.table
            @ LeftJoin(
                inputs.table,
                keys=args.group_by,
            )
            @ deferred.drop(args.checksum_col)
        )

    @property
    def generated_class_name(self) -> str:
        inputs = self.buckets.incremental_params.inputs
        return f"{inputs.__name__}BucketedInputs"
