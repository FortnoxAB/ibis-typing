from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import libcst as cst
from attrs import frozen
from libcst import matchers as m
from libcst.matchers import DoNotCareSentinel


@frozen
class Attr:
    attr: str

    def __rmatmul__(self, obj: str) -> cst.Attribute:
        return cst.Attribute(value=cst.Name(obj), attr=cst.Name(self.attr))


@frozen
class Call:
    args: Sequence[cst.Arg] = ()

    def __rmatmul__(self, func: cst.BaseExpression) -> cst.Call:
        args = [arg.with_changes(comma=cst.MaybeSentinel.DEFAULT) for arg in self.args]
        return cst.Call(func=func, args=args)


@frozen
class MatMul:
    right: cst.BaseExpression

    def __rmatmul__(self, left: cst.BaseExpression) -> cst.BinaryOperation:
        # Parenthesize left operator if it's a binary operation
        # to ensure correct order of operations.
        if (
            isinstance(left, cst.BinaryOperation)
            and not isinstance(left.operator, cst.MatrixMultiply)
        ) or isinstance(left, (cst.Comparison, cst.BooleanOperation)):
            left = left @ Parenthesize()
        return cst.BinaryOperation(left, cst.MatrixMultiply(), self.right)


@frozen
class Parenthesize:
    def __rmatmul__(self, left: cst.BaseExpression) -> cst.BaseExpression:
        return left.with_changes(
            lpar=[cst.LeftParen()],
            rpar=[cst.RightParen()],
        )


@frozen
class MatchAttr:
    attr: str

    def __rmatmul__(self, obj: str) -> m.Attribute:
        return m.Attribute(value=m.Name(obj), attr=m.Name(self.attr))


@frozen
class MatchCall:
    args: Any = DoNotCareSentinel.DEFAULT

    def __rmatmul__(self, func) -> m.Call:
        return m.Call(func, self.args)


@frozen
class Matches:
    matcher: Any

    def __rmatmul__(self, node: Any) -> bool:
        return m.matches(node, self.matcher)
