from __future__ import annotations

from ibis_typing import samples, schema_writer
from ibis_typing.samples.generated import sample_schemas


def test_update_expected_is_false_by_default(update_expected: bool):
    assert update_expected is False


def test_generate_ibis_expression_schema_packages(update_expected: bool):
    expr_schema_pkgs = {
        samples: sample_schemas,
    }

    expr_to_schema_package = {
        expr: schema_pkg
        for expr_pkg, schema_pkg in expr_schema_pkgs.items()
        for expr in schema_writer.list_expressions_in_package(expr_pkg)
    }

    schema_writer.generate_schemas_with_diff_check(
        expr_to_schema_package, update_expected
    )
