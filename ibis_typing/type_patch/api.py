from __future__ import annotations

from typing import TYPE_CHECKING, Any, overload

import ibis
from ibis import Value, ir

from .patchers import FunctionOverloadPatcher, TypeCheckingModulePatcher


def get_patchers():
    functions = [
        desc,
        ifelse,
        cases,
        coalesce,
        greatest,
        least,
        or_,
        and_,
    ]
    return [
        TypeCheckingModulePatcher(__file__),
        *[FunctionOverloadPatcher(func) for func in functions],
    ]


@overload
def desc(expr: it.NameOrTypeOrValue, /, *, nulls_first: bool = False) -> ir.Value: ...  # type: ignore
def desc(expr, /, *, nulls_first: bool = False) -> ir.Value:
    return ibis.desc(expr, nulls_first=nulls_first)


@overload
def ifelse[V: Value](condition: Any, true_expr: V, false_expr: V) -> V: ...
@overload
def ifelse[V: Value](condition: Any, true_expr: V, false_expr: Any) -> V: ...
@overload
def ifelse[V: Value](condition: Any, true_expr: Any, false_expr: V) -> V: ...
@overload
def ifelse(condition, true_expr, false_expr) -> ir.Value: ...
def ifelse(condition, true_expr, false_expr):
    return ibis.ifelse(condition, true_expr, false_expr)


@overload
def cases[V: Value](
    branch: tuple[ir.BooleanValue, V],
    *branches: tuple[ir.BooleanValue, V],
    else_: V | None,
) -> V: ...
@overload
def cases[V: Value](
    branch: tuple[Any, V],
    *branches: Any,
    else_: Any | None,
) -> V: ...
@overload
def cases(branch, *branches, else_=None) -> ir.Value: ...
def cases(branch, *branches, else_=None):
    return ibis.cases(branch, *branches, else_=else_)


@overload
def coalesce[V: Value](arg: V, *args: Any) -> V: ...
@overload
def coalesce(arg, *args) -> ir.Value: ...
def coalesce(arg, *args):
    return ibis.coalesce(*args)


@overload
def greatest[V: Value](arg: V, *args: Any) -> V: ...
@overload
def greatest(arg, *args) -> ir.Value: ...
def greatest(arg, *args):
    return ibis.greatest(*args)


@overload
def least[V: Value](arg: V, *args: Any) -> V: ...
@overload
def least(arg, *args) -> ir.Value: ...
def least(arg, *args):
    return ibis.least(*args)


@overload
def or_(*predicates: ir.BooleanValue) -> ir.BooleanValue: ...
@overload
def or_(*predicates: bool) -> bool: ...
def or_(*predicates):
    return ibis.or_(*predicates)


@overload
def and_(*predicates: ir.BooleanValue) -> ir.BooleanValue: ...
@overload
def and_(*predicates: bool) -> bool: ...
def and_(*predicates):
    return ibis.and_(*predicates)


if TYPE_CHECKING:
    from ibis_typing import ibis_types as it

    _ = it
