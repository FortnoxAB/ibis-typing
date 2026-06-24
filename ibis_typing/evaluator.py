"""Construct Expression tables by dynamic dependency injection.

In case of IncrementalExpression, construct from ChecksumBuckets and prior state.

1. Provide prior_table_provider where previous runs of ChecksumBuckets and IncrementalTable exist.
2. Provide input_table_provider as usual.
3. Construct increment
4. Merge increment with prior based on IncrementalModel.group_by selecting the increment in favor over old values.
"""

from __future__ import annotations

import inspect
import logging
import typing
from collections.abc import MutableMapping
from typing import cast

from attrs import frozen
from ibis import literal

from . import (
    ChecksumBuckets,
    Expression,
    IbisSchema,
    IbisTable,
    IncrementalExpression,
    table_provider,
    this,
)
from .checksum_buckets import AsIncrementedBuckets
from .ibis_pyarrow import EvaluateExpr
from .ibis_time import TimestampNow
from .ibis_utils import Aggregate
from .table_provider import FilteredTableProvider, TableProvider, TableProviders

logger = logging.getLogger(__name__)


def from_expression[E: Expression](
    target_table: type[E],
    *inputs: IbisTable,
    table_providers: TableProviders = (),
    cache: MutableMapping[type[IbisSchema], IbisTable] | None = None,
) -> IbisTable[E]:
    # Enable explicit cache to allow checking evaluated Expression tree.
    cache = cache if cache is not None else {}

    used = set()
    inputs_by_type = {table.table_schema: table for table in inputs}
    cache.update(inputs_by_type)
    providers = cast(TableProviders, (used.add, cache.get, *table_providers))

    provider = ExpressionTableProvider(providers, cache)
    table = provider(target_table)

    if unused := set(inputs_by_type) - set(used):
        raise ValueError(f"There are unused input schemas: {unused}")

    assert table
    return table


_chained = table_provider.chain_providers


def evaluate_incremental[E: IncrementalExpression](
    expr: type[E],
    input_table_providers: TableProviders,
    prior_table_providers: TableProviders,
) -> IbisTable[E]:
    """Construct an Incremental Expression based on prior states.

    Note: Does not verify uniqueness of output rows.
    That is to be implemented by the consumer.
    The expression test fixtures implement this check.
    """
    if not (prior := _chained(*prior_table_providers)(expr)):
        return from_expression(expr, table_providers=input_table_providers)

    increment = construct_increment(
        expr,
        input_providers=input_table_providers,
        prior_providers=prior_table_providers,
    )
    return merge_increment(prior, increment)


def construct_increment[E: IncrementalExpression](
    expr: type[E],
    input_providers: TableProviders,
    prior_providers: TableProviders,
) -> IbisTable[E]:
    """Construct increment for an Incremental Expression based on prior state."""
    if issubclass(expr, ChecksumBuckets):
        buckets = from_expression(expr, table_providers=input_providers)

        prior = _chained(*prior_providers)(expr)
        timestamp = _chained(*input_providers)(TimestampNow)

        assert prior
        assert timestamp

        buckets_cb = cast(IbisTable[ChecksumBuckets], buckets)
        prior_cb = cast(IbisTable[ChecksumBuckets], prior)
        return cast(
            IbisTable[E], expr.construct_increment(buckets_cb, prior_cb, timestamp)
        )

    bucket_provider = ChecksumBucketsIncrementTableProvider(
        expr,
        table_providers=input_providers,
        prior_providers=prior_providers,
    )
    return from_expression(expr, table_providers=[bucket_provider, *input_providers])


def merge_increment[E: IncrementalExpression](
    prior: IbisTable[E], increment: IbisTable[E]
) -> IbisTable[E]:
    """Make an expression merge via .group_by and .updated_at_col.

    Note: Does not verify row uniqueness.
    If multiple rows exists per key, the behavior is undefined.
    """
    schema = prior.table_schema
    union = increment.table.union(prior.table)
    args = schema.incremental_params
    table = union @ Aggregate(
        by=args.group_by,
        expr={
            col: this[col].argmax(this[args.updated_at_col])
            for col in schema.table_schema
            if col not in args.group_by
        },
    )

    return schema.of(table)


def check_increment[E: IncrementalExpression](increment: IbisTable[E]):
    """Check that IncrementalExpression has no duplicate rows on .group_by."""
    expr = increment.table_schema
    col_name = "count"

    group_by = expr.incremental_params.group_by
    table = increment.table @ Aggregate(by=group_by, expr={col_name: this.count()})

    key_row_check = table[col_name].max().fill_null(literal(0))
    if key_row_check @ EvaluateExpr() > 1:
        raise ValueError(f"Duplicate rows found for incremental key of {expr.__name__}")


@frozen
class ExpressionTableProvider:
    """Provides Expression tables recursively, and raises on missing inputs."""

    table_providers: TableProviders
    cache: MutableMapping

    def __call__[S: IbisSchema](self, schema: type[S]) -> IbisTable[S] | None:
        if not issubclass(schema, Expression):
            return None

        provider = _chained(*self.table_providers, self, RaiseWithSchemaTrace())
        inputs = schema.get_parameter_schema_types()
        kwargs = {name: provider(schema) for name, schema in inputs.items()}
        table = schema.from_expression(**kwargs)
        self.cache[schema] = table
        return cast(IbisTable[S], table)


@frozen
class RaiseWithSchemaTrace(TableProvider):
    """Raise ValueError with trace from input -> output schema."""

    def __call__(self, schema):
        schemas = _get_call_arg_from_stack(_chained(), filename=table_provider.__file__)
        top_schemas = _get_call_arg_from_stack(from_expression, filename=__file__)

        trace = "\n\t".join(
            f"{schema.__module__}.{schema.__qualname__}"
            for schema in (*schemas, *top_schemas)
        )
        raise ValueError(f"Missing input schema. Trace input -> output:\n\t{trace}")


def _get_call_arg_from_stack(
    fun: typing.Callable[..., typing.Any], filename: str
) -> list:
    param = next(iter(inspect.signature(fun).parameters))
    name = getattr(fun, "__name__", None)
    return [
        frame.frame.f_locals[param]
        for frame in inspect.stack()
        if frame.filename == filename and frame.function == name
    ]


@frozen
class ChecksumBucketsIncrementTableProvider(TableProvider):
    """Provide ChecksumBucketsIncrement for specific IncrementalExpression."""

    expr: type[IncrementalExpression]

    table_providers: TableProviders
    prior_providers: TableProviders

    def __call__(self, schema):
        if not issubclass(schema, ChecksumBuckets):
            return None

        prior_provider = FilteredTableProvider(
            self.prior_providers, include=[self.expr]
        )
        return from_expression(
            schema @ AsIncrementedBuckets(self.expr),
            table_providers=(prior_provider, *self.table_providers),
        )
