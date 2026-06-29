"""Integration of DBT Model via ibis Expression classes."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from enum import StrEnum
from typing import Any, Self

import attrs
from attrs import frozen

from ibis_typing import Expression, IbisDbSchema, it, naming


@frozen
class DbtModel[E: Expression]:
    """DBT model based on an Expression class."""

    expr: type[E]
    config: ModelConfig

    name: str | None = None
    prefix: str = ""

    @property
    def table_name(self):
        return self.name or (self.prefix + naming.snake_case(self.expr.__name__))

    @property
    def db_schema(self) -> type[IbisDbSchema]:
        return type(
            self.expr.__name__,
            (IbisDbSchema, self.expr),
            {"table_name": self.table_name, "table_namespace": self._namespace},
        )

    @property
    def _namespace(self) -> tuple[str, str]:
        conf = self.config
        assert conf.database
        assert conf.schema
        return conf.database, conf.schema


@frozen
class DbtSource[S: IbisDbSchema]:
    """Mark-up for a DBT Source table.

    See
    https://docs.getdbt.com/docs/build/sources?version=2.0&name=Fusion#declaring-a-source
    """

    db_schema: type[S]

    def _get_dbt_source_name(self) -> str:
        # By default, schema will be the same as name.
        return self.db_schema.table_namespace[1]

    dbt_source_name: str = attrs.field(
        default=attrs.Factory(_get_dbt_source_name, takes_self=True)
    )


@frozen
class GeneralConfig:
    """General configurations applicable across multiple DBT resource types.

    See
    https://docs.getdbt.com/reference/model-configs?version=2.0&name=Fusion#general-configurations
    """

    database: str | None = None
    schema: str | None = None
    alias: str | None = None

    tags: Sequence[str] | None = None

    enabled: bool | None = None

    pre_hook: Sequence[str] | None = None
    post_hook: Sequence[str] | None = None

    persist_docs: Mapping | None = None
    full_refresh: bool | None = None
    meta: Mapping | None = None
    grants: Mapping | None = None
    contract: Mapping | None = None
    event_time: it.NameOrType | None = None

    kwargs: Any | None = None  # Other fields and backend-specific config

    def with_namespace(self, database: str, schema: str) -> Self:
        return attrs.evolve(self, database=database, schema=schema)

    def add_tags(self, tags: Sequence[str] | None) -> Self:
        all_tags = (*(self.tags or ()), *(tags or ()))
        return attrs.evolve(self, tags=list(all_tags) or None)


@frozen
class ModelConfig(GeneralConfig):
    """Configuration for DBT models, incremental or not.

    See
    https://docs.getdbt.com/reference/model-configs?version=2.0&name=Fusion#model-specific-configurations
    """

    materialized: Materialized | str | None = None

    incremental_strategy: IncrementalStrategy | None = None
    unique_key: Sequence[it.NameOrType] | None = None
    on_schema_change: OnSchemaChange | None = None

    def __attrs_post_init__(self):
        if self.incremental_strategy:
            assert self.unique_key is not None


class PlainStrEnum(StrEnum):
    """StrEnum, but with simple str() representation."""

    def __str__(self):
        return repr(self._value_)

    def __repr__(self):
        return repr(self._value_)


class Materialized(PlainStrEnum):
    """Materialization strategy for DBT models.

    Note: Custom materialization strategies are handled as plain strings.

    See
    https://docs.getdbt.com/docs/build/materializations?version=2.0
    """

    table = "table"
    view = "view"
    incremental = "incremental"
    ephemeral = "ephemeral"
    materialized_view = "materialized view"


class OnSchemaChange(PlainStrEnum):
    """Strategy for handling schema changes in incremental models.

    See
    https://docs.getdbt.com/docs/build/incremental-models?version=2.0&name=Fusion#what-if-the-columns-of-my-incremental-model-change
    """

    ignore = "ignore"
    fail = "fail"
    append_new_columns = "append_new_columns"
    sync_all_columns = "sync_all_columns"


class IncrementalStrategy(PlainStrEnum):
    """Strategy for updating incremental models.

    See
    https://docs.getdbt.com/docs/build/incremental-strategy?version=2.0&name=Fusion#supported-incremental-strategies-by-adapter
    """

    append = "append"
    merge = "merge"
    delete_insert = "delete+insert"
    insert_overwrite = "insert_overwrite"
    microbatch = "microbatch"
