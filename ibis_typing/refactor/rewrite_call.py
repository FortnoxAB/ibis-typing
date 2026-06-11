from __future__ import annotations

import libcst
from attrs import frozen

from ibis_typing.refactor import cst
from ibis_typing.refactor.ibis_cst import CstRule, IbisTransformer


@frozen
class IbisFuncToMethodRule(CstRule[libcst.Call]):
    func: str
    method: str

    left_kw: str | None = None

    kw_tail: bool = False

    @property
    def func_matcher(self):
        return "ibis" @ cst.MatchAttr(self.func) @ cst.MatchCall()

    def apply_extension_method(self, right):
        return cst.MatMul("it" @ cst.Attr(self.method) @ cst.Call(right))

    def apply(self, node: libcst.Call) -> libcst.BaseExpression | None:
        if not node @ cst.Matches(self.func_matcher):
            return None

        def _is_left_kw(arg: libcst.Arg) -> bool:
            return bool((kw := arg.keyword) and kw.value == self.left_kw)

        if self.left_kw:
            if not (
                kwarg := next((arg for arg in node.args if _is_left_kw(arg)), None)
            ):
                return None

            left, right = (
                kwarg.value,
                [arg for arg in node.args if not _is_left_kw(arg)],
            )
        else:
            head, *tail = node.args
            if head.star:
                return None

            left, right = head.value, tail

        return left @ self.apply_extension_method(right)


ibis_api_transformer = IbisTransformer(
    import_stmt="from ibis_typing import it",
    rules=[
        IbisFuncToMethodRule("desc", "Desc"),
        IbisFuncToMethodRule("ifelse", "IfElse"),
        IbisFuncToMethodRule("cases", "Cases", left_kw="else_"),
        IbisFuncToMethodRule("coalesce", "FillNull"),
        IbisFuncToMethodRule("greatest", "Greatest"),
        IbisFuncToMethodRule("least", "Least"),
        IbisFuncToMethodRule("and_", "And"),
        IbisFuncToMethodRule("or_", "Or"),
    ],
)
