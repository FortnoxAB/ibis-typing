"""Compile DBT Model to DBT SQL."""

from __future__ import annotations

import functools
import re
from argparse import Namespace
from collections.abc import Mapping
from typing import Any

import attrs

from ibis_typing import ChecksumBuckets

from ..revertible import AsRevertible, ExpressionExport
from . import dbt_ibis_constructor
from .dbt_ibis_constructor import DbtRefTableProvider, DbtSelfRefProvider
from .dbt_model import DbtModel, GeneralConfig, Materialized
from .dbt_snapshot import DbtSnapshot


def dbt_model_to_dbt_sql(
    model: DbtModel, dialect: str, *, ref_provider: DbtRefTableProvider
) -> str:
    if isinstance(model, DbtSnapshot):
        return dbt_snapshot_to_dbt_sql(model, dialect, ref_provider=ref_provider)

    from_source = dbt_ibis_constructor.construct_dbt_model(model.expr, ref_provider)

    from_source_sql = from_source.table.to_sql(dialect)

    if model.config.materialized != Materialized.incremental:
        sql = from_source_sql
    else:
        increment = (
            dbt_ibis_constructor.construct_dbt_bucket_increment(
                model.expr, ref_provider
            )
            if issubclass(model.expr, ChecksumBuckets)
            else dbt_ibis_constructor.construct_dbt_model(
                model.expr, ref_provider, buckets_update=True
            )
        )

        increment_sql = increment.table.to_sql(dialect)

        sql = as_incremental_macro(from_source_sql, inc_sql=increment_sql)

    dbt_sql = process_sql_dbt_tokens(sql)
    config_sql = config_to_jinja(model.config)

    return config_sql + dbt_sql


def dbt_snapshot_to_dbt_sql(
    snapshot: DbtSnapshot, dialect: str, *, ref_provider: DbtRefTableProvider
) -> str:
    exported = snapshot.expr @ AsRevertible(ExpressionExport)
    snapshot_table = dbt_ibis_constructor.construct_dbt_model(exported, ref_provider)

    table_sql = snapshot_table.table.to_sql(dialect)

    dbt_sql = process_sql_dbt_tokens(table_sql)
    config_jinja = config_to_jinja(snapshot.config)

    return as_snapshot_macro(config_jinja + dbt_sql, table_name=snapshot.table_name)


def as_incremental_macro(full_sql: str, inc_sql: str) -> str:
    """Wrap SQL in a DBT Jinja conditional for incremental or full refresh.

    >>> as_incremental_macro("SELECT 1", "SELECT 2")
    '{% if is_incremental() %}\\nSELECT 2\\n{% else %}\\nSELECT 1\\n{% endif %}'

    See
    https://docs.getdbt.com/docs/build/incremental-models?version=2.0&name=Fusion#filtering-rows-on-an-incremental-run
    """
    return f"{{% if is_incremental() %}}\n{inc_sql}\n{{% else %}}\n{full_sql}\n{{% endif %}}"


def as_snapshot_macro(sql: str, *, table_name: str):
    """Wrap SQL in a DBT Jinja conditional for incremental or full refresh.

    Note: This uses DBT legacy SQL configuration.
    Consider using the all-YML configuration approach for snapshots.

    >>> as_snapshot_macro("SELECT 2", table_name="table")
    '{% snapshot table %}\\nSELECT 2\\n{% endsnapshot %}'

    See
    https://docs.getdbt.com/reference/resource-configs/snapshots-jinja-legacy?version=2.0&name=Fusion#snapshot-specific-configurations
    https://docs.getdbt.com/reference/snapshot-configs?version=2.0#configuring-snapshots
    """
    return f"{{% snapshot {table_name} %}}\n{sql}\n{{% endsnapshot %}}"


def process_sql_dbt_tokens(sql: str) -> str:
    """Format DBT Jinja function calls for `this`, `ref`, and `source` from SQL tokens.

    >>> process_sql_dbt_tokens('SELECT * FROM "__dbt_this__"')
    'SELECT * FROM {{ this }}'
    >>> process_sql_dbt_tokens('SELECT * FROM "__dbt_ref__my_model__dbt_ref__"')
    'SELECT * FROM {{ ref("my_model") }}'
    >>> process_sql_dbt_tokens(
    ...     'SELECT * FROM "__dbt_src__my_source__dbt_sep__my_table__dbt_src__"'
    ... )
    'SELECT * FROM {{ source("my_table", "my_source") }}'

    See
    https://docs.getdbt.com/reference/dbt-jinja-functions/this?version=2.0&name=Fusion
    https://docs.getdbt.com/reference/dbt-jinja-functions/ref?version=2.0&name=Fusion#definition
    https://docs.getdbt.com/reference/dbt-jinja-functions/source?version=2.0&name=Fusion#example
    """
    self = DbtSelfRefProvider
    cls = DbtRefTableProvider
    subs = [
        (
            re.compile(rf'"?{self.SELF_TOKEN}"?'),
            "{{ this }}",
        ),
        (
            re.compile(rf'"?{cls.REF_TOKEN}(.*?){cls.REF_TOKEN}"?'),
            r'{{ ref("\1") }}',
        ),
        (
            re.compile(rf'"?{cls.SRC_TOKEN}(.*?){cls.SEP_TOKEN}(.*?){cls.SRC_TOKEN}"?'),
            r'{{ source("\2", "\1") }}',
        ),
    ]

    def reduce(sub, s):
        pattern, new = sub
        return pattern.sub(new, s)

    return functools.reduce(lambda s, sub: reduce(sub, s), subs, sql)


def config_to_jinja(config: GeneralConfig) -> str:
    """Format a DBT Jinja config header.

    >>> from ibis_typing.dbt.dbt_model import IncrementalStrategy, ModelConfig
    >>> config_to_jinja(
    ...     ModelConfig(
    ...         incremental_strategy=IncrementalStrategy.merge,
    ...         unique_key=[],
    ...         kwargs={"properties": {}},
    ...     )
    ... )
    "{{ config(incremental_strategy='merge', unique_key=[], properties={}) }}\\n"
    """
    kwargs = {
        **{
            key: val
            for key, val in attrs.asdict(config, recurse=False).items()
            if val is not None
            if key != "kwargs"
        },
        **(config.kwargs or {}),
    }
    namespace = Namespace(**_tuple_as_list(kwargs))
    py_block = str(namespace).replace(Namespace.__name__, "config", 1)
    return "{{ " + py_block + " }}\n"


def _tuple_as_list(obj: Any) -> Any:
    """DBT internals requires strict `list` type arguments."""
    if isinstance(obj, tuple):
        return list(obj)
    if isinstance(obj, Mapping):
        return {key: _tuple_as_list(val) for key, val in obj.items()}
    return obj
