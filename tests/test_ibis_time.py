import datetime

import pytest
from ibis import literal

from ibis_typing.ibis_ops import ColumnChecksum
from ibis_typing.ibis_time import AddMonths, MonthsSince, StartOfMonth
from ibis_typing.utils import StrDate
from tests.conftest import SimpleSchema


@pytest.mark.parametrize("months", list(range(-42, 42, 7)))
def test_add_months(evaluate_expr, months):
    now = StrDate("2020-01-11")

    expr = literal(now.date) @ AddMonths(months)
    actual = evaluate_expr(expr, datetime.date)

    assert actual == now.plus_months(months).date


@pytest.mark.parametrize("value", [0, 1, 2])
def test_column_checksum(evaluate_expr, ibis_dialect, value):
    rows = [
        SimpleSchema(id=0, value=value + 1),
        SimpleSchema(id=1, value=value + 2),
    ]
    table = SimpleSchema.of_rows(rows).table

    expr = table[SimpleSchema.cols.value] @ ColumnChecksum()
    actual = evaluate_expr(expr)

    expected_lookup = {
        "duckdb": [6764638988363571842, 7800405281646302356, 480823984174830650],
        "trino": [7171930684550795574, 1683313830075110705, -7775161972590745618],
    }
    expected = expected_lookup[ibis_dialect][value]

    assert actual == expected


@pytest.mark.parametrize("months", list(range(-42, 42, 7)))
def test_diff_months(evaluate_expr, months):
    now = StrDate("2020-01-01")

    expr = literal(now.plus_months(months).date) @ MonthsSince(
        literal(now.plus(20).date)
    )
    actual = evaluate_expr(expr)

    assert actual == months


@pytest.mark.parametrize("days", list(range(-42, 42, 7)))
def test_truncate_month(evaluate_expr, days):
    now = StrDate("2020-01-01").plus(days)

    expr = literal(now.date) @ StartOfMonth()
    expected = now.month_start.date
    actual = evaluate_expr(expr, datetime.date)

    assert actual == expected
