from pathlib import Path

from ibis_typing.dbt import dbt_sql_compiler
from ibis_typing.dbt.dbt_ibis_constructor import DbtRefTableProvider
from ibis_typing.samples import dbt_models

from .. import generated

SQL_DIR_NAME = "__ibis_sql"
SQL_DIR = Path(generated.__file__).parent / SQL_DIR_NAME


def test_generate_ibis_dbt_sql(update_expected):
    model_lookup = dbt_models.get_dbt_model_lookup()
    source_lookup = dbt_models.get_dbt_source_lookup()
    ref_provider = DbtRefTableProvider(model_lookup, source_lookup)

    new = {
        SQL_DIR / (model.table_name + ".sql"): dbt_sql_compiler.dbt_model_to_dbt_sql(
            model,
            dialect="duckdb",
            ref_provider=ref_provider,
        )
        for model in model_lookup.values()
    }

    if update_expected:
        for path, sql in new.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(sql)

    prior_paths = {p for p in SQL_DIR.iterdir() if p.suffix == ".sql"}
    prior = {path: path.read_text() for path in prior_paths}

    assert new == prior
