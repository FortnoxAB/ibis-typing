import textwrap

import libcst as cst
import pytest

from ibis_typing.refactor.migrations import MIGRATIONS


def rewrite_source(source: str, module: str = "api") -> str:
    self = MIGRATIONS[module]
    tree = cst.parse_module(source)
    new_tree = tree.visit(self)
    return new_tree.code


def rewrite(src: str, module: str = "api") -> str:
    source = textwrap.dedent(src).strip()
    return rewrite_source(source, module).split("\n").pop()


def test_parenthesize_left_with_binary_operator():
    result = rewrite("ibis.desc(a + b)")
    assert result == "(a + b) @ it.Desc()"


def test_parenthesize_left_with_comparison():
    result = rewrite("ibis.ifelse(a > b, c, d)")
    assert result == "(a > b) @ it.IfElse(c, d)"


def test_parenthesize_left_with_bool_operator():
    result = rewrite("ibis.ifelse(a and b, c, d)")
    assert result == "(a and b) @ it.IfElse(c, d)"


def test_non_ibis_call_untouched():
    source = "foo.desc(x)"
    actual = rewrite_source(source)
    assert actual == source


def test_unknown_ibis_call_untouched():
    source = "ibis.table('my_table')"
    actual = rewrite_source(source)
    assert actual == source


def test_nested_calls():
    source = "ibis.ifelse(ibis.and_(a, b), x, y)"
    actual = rewrite(source)
    assert actual == "a @ it.And(b) @ it.IfElse(x, y)"


def test_ibis_api_import_injected_on_change():
    actual = rewrite_source("ibis.and_(x, y)")
    lines = actual.split("\n")
    assert lines == [
        "from ibis_typing import it",
        "x @ it.And(y)",
    ]


def test_ibis_ops_import_injected_on_change():
    actual = rewrite_source("ibis_ops.column_checksum(x)", "ibis_ops")
    lines = actual.split("\n")
    assert lines.pop(0).startswith("from ibis_typing.ibis_ops import ")
    assert lines == ["x @ ColumnChecksum()"]


@pytest.mark.parametrize(
    ["source", "output"],
    [
        (
            "ibis.desc(col)",
            "col @ it.Desc()",
        ),
        (
            "ibis.desc(col, nulls_first=True)",
            "col @ it.Desc(nulls_first=True)",
        ),
        (
            "ibis.ifelse(x, y, z)",
            "x @ it.IfElse(y, z)",
        ),
        (
            "ibis.cases((x, y), else_=z)",
            "z @ it.Cases((x, y))",
        ),
        (
            "ibis.cases((a, b), (c, d), else_=z)",
            "z @ it.Cases((a, b), (c, d))",
        ),
        (
            "ibis.coalesce(val, fallback)",
            "val @ it.FillNull(fallback)",
        ),
        (
            "ibis.coalesce(a, b, c)",
            "a @ it.FillNull(b, c)",
        ),
        (
            "ibis.greatest(a, b, c)",
            "a @ it.Greatest(b, c)",
        ),
        (
            "ibis.least(x, y)",
            "x @ it.Least(y)",
        ),
        (
            "ibis.and_(p, q, r)",
            "p @ it.And(q, r)",
        ),
        (
            "ibis.or_(p, q)",
            "p @ it.Or(q)",
        ),
    ],
)
def test_rewrite_ibis_api_func_to_method(source: str, output: str):
    actual = rewrite(source)
    assert actual == output


@pytest.mark.parametrize(
    ["source", "output"],
    [
        (
            "ibis_ops.column_checksum(x)",
            "x @ ColumnChecksum()",
        ),
        (
            "ibis_ops.parse_json(x)",
            "x @ JsonParse()",
        ),
        (
            "ibis_ops.json_format(x)",
            "x @ JsonFormat()",
        ),
        (
            "ibis_ops.uuid_from_int(x)",
            "x @ IntToUUID()",
        ),
        (
            "ibis_ops.luhn_check(x)",
            "x @ LuhnCheck()",
        ),
    ],
)
def test_rewrite_ibis_ops_func_to_method(source: str, output: str):
    actual = rewrite(source, "ibis_ops")
    assert actual == output


@pytest.mark.parametrize(
    ["source", "output"],
    [
        (
            "ibis_time.truncate_month(x)",
            "x @ StartOfMonth()",
        ),
        (
            "ibis_time.diff_months(x, y)",
            "x @ MonthsSince(y)",
        ),
        (
            "ibis_time.diff_days(x, y)",
            "x @ DaysSince(y)",
        ),
        (
            "ibis_time.add_months(x, y)",
            "x @ AddMonths(y)",
        ),
        (
            "ibis_time.add_days(x, y)",
            "x @ AddDays(y)",
        ),
    ],
)
def test_rewrite_ibis_time_func_to_method(source: str, output: str):
    actual = rewrite(source, "ibis_time")
    assert actual == output
