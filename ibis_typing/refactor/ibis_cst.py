from __future__ import annotations

import abc
from collections.abc import Sequence
from typing import ClassVar

import libcst
from attr import dataclass
from attrs import frozen
from libcst import matchers

from ibis_typing.extension_method import ExtensionMethod
from ibis_typing.refactor import cst


@dataclass
class IbisTransformer(libcst.CSTTransformer):
    rules: Sequence[IbisFuncToMethodRule]

    import_line: str | None = None
    import_from: str | None = None

    _changed: bool = False

    @property
    def import_stmt(self) -> str:
        rules = ", ".join(r.method for r in self.rules)
        return (
            f"from {self.import_from} import {rules}"
            if self.import_from
            else self.import_line or ""
        )

    def visit_Module(self, node: libcst.Module):
        self._changed = False

    def leave_Call(self, original_node: libcst.Call, updated_node: libcst.Call):
        for rule in self.rules:
            if node := updated_node @ rule:
                self._changed = True
                return node

        return updated_node

    def leave_Module(
        self, original_node: libcst.Module, updated_node: libcst.Module
    ) -> libcst.Module:
        if not self._changed:
            return updated_node

        import_stmt = libcst.parse_statement(self.import_stmt)
        new_body = (import_stmt, *updated_node.body)
        return updated_node.with_changes(body=new_body)


class CstRule[T: libcst.CSTNode](ExtensionMethod[T, libcst.CSTNode | None], abc.ABC):
    """Base for CST rewrite rules.

    Implemented as an ExtensionMethod to allow for chaining and deferred application.
    """

    @abc.abstractmethod
    def apply(self, node: T) -> libcst.CSTNode | None:
        """Apply the rewrite rule to the given node."""

    def __rmatmul__(self, other: T) -> libcst.CSTNode | None:
        return self.apply(other)


@frozen
class IbisFuncToMethodRule(CstRule[libcst.Call]):
    func: str
    method: str

    left_kw: str | None = None

    kw_tail: bool = False

    # Override in subclass if using module-namespaced calls
    func_module: ClassVar[str | None] = None
    method_module: ClassVar[str | None] = None

    def apply(self, node: libcst.Call) -> libcst.BaseExpression | None:
        if not node @ cst.Matches(
            (
                self.func_module @ cst.MatchAttr(self.func)
                if self.func_module
                else matchers.Name(self.func)
            )
            @ cst.MatchCall()
        ):
            return None

        split = self._split_args(node)
        if split is None:
            return None
        left, right = split

        return left.value @ cst.MatMul(
            (
                self.method_module @ cst.Attr(self.method)
                if self.method_module
                else libcst.Name(self.method)
            )
            @ cst.Call(right)
        )

    def _split_args(
        self, node: libcst.Call
    ) -> tuple[libcst.Arg, list[libcst.Arg]] | None:
        """Split call args into the receiver arg and the remaining args."""
        if self.left_kw:
            kwarg = next((arg for arg in node.args if self._is_left_kw(arg)), None)
            if not kwarg:
                return None
            return kwarg, [arg for arg in node.args if not self._is_left_kw(arg)]

        head, *tail = node.args
        if head.star:
            return None
        return head, tail

    def _is_left_kw(self, arg: libcst.Arg) -> bool:
        return bool((kw := arg.keyword) and kw.value == self.left_kw)
