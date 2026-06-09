from hypothesis import given
from hypothesis import strategies as st
from ibis import literal

from ibis_typing.ibis_time import AddMonths, MonthsSince, StartOfMonth
from ibis_typing.utils import StrDate


@given(months=st.integers(-42, 42))
def test_add_months(evaluate_expr, months, today):
    expr = literal(today.date) @ AddMonths(months)
    expected = today.plus_months(months).date
    actual = evaluate_expr(expr)
    assert actual == expected


@given(months=st.integers(-42, 42))
def test_diff_months(evaluate_expr, months):
    today = StrDate("2020-01-20")
    expr = literal(today.plus_months(months).date) @ MonthsSince(literal(today.date))
    actual = evaluate_expr(expr)
    assert actual == months


@given(days=st.integers(-999, 999))
def test_truncate_month(evaluate_expr, days):
    now = StrDate("2020-01-01").plus(days)
    expr = literal(now.date) @ StartOfMonth()
    expected = now.month_start.date
    actual = evaluate_expr(expr)
    assert actual == expected
