from collections.abc import Mapping

from ibis_typing import Expression, IbisDbSchema, IbisSchema, naming, samples
from ibis_typing.dbt import (
    DbtModel,
    DbtSnapshot,
    DbtSource,
    ModelConfig,
    SnapshotConfig,
    dbt_model_resolver,
)
from ibis_typing.dbt.dbt_model import IncrementalStrategy, Materialized
from ibis_typing.dbt.dbt_snapshot import SnapshotStrategy
from ibis_typing.ibis_time import TimestampNow
from ibis_typing.samples.sample_incremental_calendar import Calendar, CalendarWidth
from ibis_typing.samples.sample_transforms import CircleParameters

my_namespace = ("my_database", "my_schema")


def get_dbt_model_lookup() -> Mapping[type[Expression], DbtModel]:
    resolver = dbt_model_resolver.DbtModelResolver(samples)

    models = {
        # Provide timestamp as a table in order to use a fix timestamp per DBT run.
        DbtModel(
            TimestampNow,
            config=ModelConfig(
                materialized=Materialized.table,
            ).with_namespace(*my_namespace),
        )
    }
    incremental_models = [
        DbtModel(
            expr,
            config=ModelConfig(
                materialized=Materialized.incremental,
                incremental_strategy=IncrementalStrategy.merge,
                unique_key=expr.incremental_params.group_by,
            ).with_namespace(*my_namespace),
        )
        for expr in resolver.incremental_models
    ]
    snapshots = [
        DbtSnapshot(
            expr=CalendarWidth,
            config=SnapshotConfig(
                strategy=SnapshotStrategy.timestamp,
                unique_key=CalendarWidth.incremental_params.group_by,
                updated_at=CalendarWidth.incremental_params.updated_at_col,
            ).with_namespace(*my_namespace),
        )
    ]
    all_models = (*models, *incremental_models, *snapshots)

    return {model.expr: model for model in all_models}


def get_dbt_source_lookup() -> Mapping[type[IbisSchema], DbtSource]:
    sources = [Calendar, CircleParameters]
    return {schema: DbtSource(as_db_schema(schema)) for schema in sources}


def as_db_schema(schema: type[IbisSchema]) -> type[IbisDbSchema]:
    kwargs = {
        "table_name": naming.snake_case(schema.__name__),
        "table_namespace": my_namespace,
    }
    return type(schema.__name__, (IbisDbSchema, schema), kwargs)
