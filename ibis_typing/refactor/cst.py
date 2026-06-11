from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import libcst as cst
from attrs import frozen
from libcst import matchers as m
from libcst.matchers import DoNotCareSentinel


@frozen
class Attr:
    """Build `obj.attr` as a CST node."""

    attr: str

    def __rmatmul__(self, obj: str) -> cst.Attribute:
        return cst.Attribute(value=cst.Name(obj), attr=cst.Name(self.attr))


@frozen
class Call:
    args: Sequence[cst.Arg] = ()

    def __rmatmul__(self, func: cst.Attribute) -> cst.Call:
        args = [arg.with_changes(comma=cst.MaybeSentinel.DEFAULT) for arg in self.args]
        return cst.Call(func=func, args=args)


@frozen
class MatMul:
    right: cst.BaseExpression

    def __rmatmul__(self, left: cst.BaseExpression) -> cst.BinaryOperation:
        return cst.BinaryOperation(left, cst.MatrixMultiply(), self.right)


@frozen
class MatchAttr:
    attr: str

    def __rmatmul__(self, obj: str) -> m.Attribute:
        return m.Attribute(value=m.Name(obj), attr=m.Name(self.attr))


@frozen
class MatchCall:
    args: Any = DoNotCareSentinel.DEFAULT

    def __rmatmul__(self, func: m.Attribute) -> m.Call:
        return m.Call(func, self.args)


@frozen
class Matches:
    matcher: Any

    def __rmatmul__(self, node: Any) -> bool:
        return m.matches(node, self.matcher)
