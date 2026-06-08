import pytest
from ibis import literal

from ibis_typing import ibis_api as api

l = literal  # noqa


@pytest.mark.parametrize("cond", [True, False])
def test_IfElse(evaluate_expr, cond):
    then, else_ = 1, 2
    expr = l(cond) @ api.IfElse(l(then), l(else_))
    expected = then if cond else else_
    actual = evaluate_expr(expr)
    assert actual == expected


@pytest.mark.parametrize("cond", [True, False])
def test_Cases(evaluate_expr, cond):
    then, else_ = 1, 2
    expr = l(else_) @ api.Cases((l(cond), l(then)))
    expected = then if cond else else_
    actual = evaluate_expr(expr)
    assert actual == expected


@pytest.mark.parametrize("is_null", [True, False])
def test_FillNull(evaluate_expr, is_null):
    left, right = 1, 2
    expr = l(None if is_null else left) @ api.FillNull(l(right))
    expected = right if is_null else left
    actual = evaluate_expr(expr)
    assert actual == expected


@pytest.mark.parametrize("a", [1, 2])
@pytest.mark.parametrize("b", [1, 2])
def test_Greatest(evaluate_expr, a, b):
    expr = l(a) @ api.Greatest(l(b))
    expected = max(b, a)
    actual = evaluate_expr(expr)
    assert actual == expected


@pytest.mark.parametrize("a", [1, 2])
@pytest.mark.parametrize("b", [1, 2])
def test_Least(evaluate_expr, a, b):
    expr = l(a) @ api.Least(l(b))
    expected = min(b, a)
    actual = evaluate_expr(expr)
    assert actual == expected


@pytest.mark.parametrize("a", [True, False])
@pytest.mark.parametrize("b", [True, False])
def test_And(evaluate_expr, a, b):
    expr = l(a) @ api.And(l(b))
    expected = all([a, b])
    actual = evaluate_expr(expr)
    assert actual == expected


@pytest.mark.parametrize("a", [True, False])
@pytest.mark.parametrize("b", [True, False])
def test_Or(evaluate_expr, a, b):
    expr = l(a) @ api.Or(l(b))
    expected = any([a, b])
    actual = evaluate_expr(expr)
    assert actual == expected
