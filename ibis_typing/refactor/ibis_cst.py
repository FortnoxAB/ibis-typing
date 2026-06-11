from __future__ import annotations

import abc
from collections.abc import Sequence

import libcst as cst
from attr import dataclass

from ibis_typing.extension_method import ExtensionMethod


@dataclass
class IbisTransformer(cst.CSTTransformer):
    import_stmt: str
    rules: Sequence[CstRule]

    _changed: bool = False

    def visit_Module(self, node: cst.Module):
        self._changed = False

    def leave_Call(self, original_node: cst.Call, updated_node: cst.Call):
        for rule in self.rules:
            if node := updated_node @ rule:
                self._changed = True
                return node

        return updated_node

    def leave_Module(
        self, original_node: cst.Module, updated_node: cst.Module
    ) -> cst.Module:
        if not self._changed:
            return updated_node

        import_stmt = cst.parse_statement(self.import_stmt)
        new_body = (import_stmt, *updated_node.body)
        return updated_node.with_changes(body=new_body)


class CstRule[T: cst.CSTNode](ExtensionMethod[T, cst.CSTNode | None], abc.ABC):
    """Base for CST rewrite rules.

    Implemented as an ExtensionMethod to allow for chaining and deferred application.
    """

    @abc.abstractmethod
    def apply(self, node: T) -> cst.CSTNode | None:
        """Apply the rewrite rule to the given node."""

    def __rmatmul__(self, other: T) -> cst.CSTNode | None:
        return self.apply(other)
