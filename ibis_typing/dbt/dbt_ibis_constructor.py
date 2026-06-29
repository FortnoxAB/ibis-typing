"""Construct ibis Tables for compiling DBT SQL models."""

from __future__ import annotations

import logging
from collections.abc import Mapping

import ibis
from attrs import frozen

from ibis_typing import Expression, IbisSchema, IbisTable, evaluator
from ibis_typing.checksum_buckets import (
    AsIncrementedBuckets,
    ChecksumBuckets,
    IncrementalExpression,
)
from ibis_typing.table_provider import TableProvider

from .dbt_model import DbtModel, DbtSource

logger = logging.getLogger(__name__)


def construct_dbt_model[E: Expression](
    schema: type[E],
    ref_provider: DbtRefTableProvider,
    *,
    self: type[Expression] | None = None,
    buckets_update: bool = False,
) -> IbisTable[E]:
    logger.info(
        f"Constructing {schema.__name__}"
        if not self
        else f"Constructing {schema.__name__} for {self.__name__}"
    )
    self = self or schema
    providers = [
        DbtSelfRefProvider(self),
        *([DbtBucketProvider(schema, ref_provider)] if buckets_update else ()),
        ref_provider,
    ]
    return evaluator.from_expression(schema, table_providers=providers)


def construct_dbt_bucket_increment[M: IncrementalExpression](
    expr: type[M],
    ref_provider: DbtRefTableProvider,
) -> IbisTable[M]:
    logger.info(f"Constructing bucket increment for {expr.__name__}")
    return evaluator.construct_increment(
        expr,
        prior_providers=[DbtSelfRefProvider(expr)],
        input_providers=[ref_provider],
    )


@frozen
class DbtBucketProvider(TableProvider):
    expr: type[Expression]
    table_provider: DbtRefTableProvider

    def __call__(self, schema):
        if not issubclass(schema, ChecksumBuckets):
            return None

        assert issubclass(self.expr, IncrementalExpression)
        return construct_dbt_model(
            schema @ AsIncrementedBuckets(self.expr),
            self.table_provider,
            self=self.expr,
        )


@frozen
class DbtSelfRefProvider(TableProvider):
    self_expr: type[Expression]

    SELF_TOKEN = "__dbt_this__"

    def __call__(self, schema):
        if not issubclass(schema, self.self_expr):
            return None

        table = ibis.table(schema.table_schema, name=self.SELF_TOKEN)
        return schema.of(table)


@frozen
class DbtRefTableProvider(TableProvider):
    """Provide tables with DBT token names for compiling DBT SQL."""

    model_lookup: Mapping[type[Expression], DbtModel]
    source_lookup: Mapping[type[IbisSchema], DbtSource]

    REF_TOKEN = "__dbt_ref__"
    SRC_TOKEN = "__dbt_src__"
    SEP_TOKEN = "__dbt_sep__"

    def __call__(self, schema):
        if model := self.model_lookup.get(schema):
            schema = model.db_schema
            name = schema.table_name

            ref_name = f"{self.REF_TOKEN}{name}{self.REF_TOKEN}"
            table = ibis.table(schema.table_schema, name=ref_name)
            return schema.of(table)

        if source := self.source_lookup.get(schema):
            schema = source.db_schema
            name = schema.table_name
            src = source.dbt_source_name

            ref_name = f"{self.SRC_TOKEN}{name}{self.SEP_TOKEN}{src}{self.SRC_TOKEN}"
            table = ibis.table(schema.table_schema, name=ref_name)
            return schema.of(table)

        return None
