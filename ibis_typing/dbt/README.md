# `ibis_typing.dbt` — dbt Integration

Bridges typed `ibis_typing` [Expression](../expression.py) classes with
[DBT](https://docs.getdbt.com/) by compiling them to DBT SQL (Jinja templates).

---

## Overview

| Class / function       | Purpose                                                      |
|------------------------|--------------------------------------------------------------|
| `DbtModel`             | Wraps an `Expression` as a DBT model with its `ModelConfig`  |
| `DbtSource`            | Wraps an `IbisDbSchema` as a DBT source table                |
| `DbtSnapshot`          | Wraps an `IbisSchema` as a DBT snapshot                      |
| `ModelConfig`          | DBT model config (materialization, incremental strategy, …)  |
| `SnapshotConfig`       | DBT snapshot config (strategy, unique key, updated-at, …)    |
| `DbtModelResolver`     | Auto-discovers `Expression` implementations inside a package |
| `dbt_model_to_dbt_sql` | Compiles a `DbtModel` / `DbtSnapshot` to a DBT SQL string    |

---

## Quick Start

The canonical example lives in
[`ibis_typing/samples/dbt_models.py`](../samples/dbt_models.py).
It shows how to build model and source lookups that can be fed directly into the
SQL compiler.

```python
# ibis_typing/samples/dbt_models.py
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
        # Provide timestamp as a table so every dbt run uses a fixed timestamp.
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
```

---

## Compiling to dbt SQL

Use `DbtRefTableProvider` to wire the model and source lookups together, then
call `dbt_model_to_dbt_sql` for each model.
See [`ibis_typing/samples/tests/test_generate_ibis_dbt_sql.py`](../samples/tests/test_generate_ibis_dbt_sql.py)
for the full test that also snapshots the generated SQL to disk.

```python
from ibis_typing.dbt import dbt_sql_compiler
from ibis_typing.dbt.dbt_ibis_constructor import DbtRefTableProvider
from ibis_typing.samples import dbt_models

model_lookup = dbt_models.get_dbt_model_lookup()
source_lookup = dbt_models.get_dbt_source_lookup()
ref_provider = DbtRefTableProvider(model_lookup, source_lookup)

for model in model_lookup.values():
    sql = dbt_sql_compiler.dbt_model_to_dbt_sql(
        model,
        dialect="duckdb",
        ref_provider=ref_provider,
    )
    print(sql)
```

The compiler automatically:

- Injects a `{{ config(...) }}` Jinja header from the model's config.
- Wraps incremental models in `{% if is_incremental() %} … {% else %} … {% endif %}`.
- Wraps snapshots in `{% snapshot <name> %} … {% endsnapshot %}`.
- Replaces internal placeholder tokens with `{{ ref("…") }}`, `{{ source("…", "…") }}`,
  and `{{ this }}`.

## Auto-Discovery with `DbtModelResolver`

`DbtModelResolver` scans a Python package and returns all `Expression`
subclasses grouped by category:
