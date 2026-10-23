from __future__ import annotations

import json
import uuid

import ibis
import pytest
from ibis import literal as l

from ibis_typing.fixtures.expressions import EvaluateExpr
from ibis_typing.ibis_ops import (
    ColumnChecksum,
    IntToUUID,
    JsonFormat,
    JsonParse,
    LuhnCheck,
)


@pytest.mark.parametrize("value", [0, 1, 2])
def test_column_checksum(evaluate_expr: EvaluateExpr, ibis_dialect: str, value: int):
    rows = [
        value + 1,
        value + 2,
    ]
    table = ibis.memtable({"value": rows})

    expr = table["value"] @ ColumnChecksum()
    actual = evaluate_expr(expr)

    expected_lookup = {
        "duckdb": [6764638988363571842, 7800405281646302356, 480823984174830650],
        "trino": [7171930684550795574, 1683313830075110705, -7775161972590745618],
    }
    expected = expected_lookup[ibis_dialect][value]

    assert actual == expected


def test_json_roundtrip(evaluate_expr: EvaluateExpr):
    expected = {"string": "value", "number": 42, "object": {"array": [1, 2, 3]}}
    expr = l(json.dumps(expected)) @ JsonParse() @ JsonFormat()
    actual = evaluate_expr(expr)
    assert json.loads(actual) == expected


@pytest.mark.parametrize(
    ["int_", "uuid_"], [(1, uuid.UUID(int=1)), (-1, uuid.UUID(int=2**64 - 1))]
)
def test_uuid_from_int(evaluate_expr: EvaluateExpr, int_: int, uuid_: uuid.UUID):
    expr = l(int_) @ IntToUUID()
    expected = uuid_
    actual = evaluate_expr(expr)
    assert actual == expected


@pytest.mark.parametrize(
    ["pnr", "is_valid"],
    [
        ("8112189876", True),
        ("9503271414", True),
        ("9503271415", False),
    ],
)
def test_luhn_check(evaluate_expr: EvaluateExpr, pnr: str, is_valid: bool):
    expr = l(pnr) @ LuhnCheck()
    expected = is_valid
    actual = evaluate_expr(expr)
    assert actual == expected
