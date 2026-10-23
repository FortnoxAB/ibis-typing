from __future__ import annotations

from typing import overload

from ibis import ir

from .patchers import (
    MethodOverloadPatcher,
    TypingOverloadImportPatcher,
)


def get_patchers():
    methods = [
        BooleanIfElse,
    ]
    return [
        TypingOverloadImportPatcher(),
        *[MethodOverloadPatcher(patch) for patch in methods],
    ]


class BooleanIfElse(ir.BooleanValue):
    @overload
    def ifelse[T: ir.Value](self, true_expr: T, false_expr: ir.Value, /) -> T: ...
    @overload
    def ifelse[T: ir.Value](self, true_expr: ir.Value, false_expr: T, /) -> T: ...
    def ifelse(self, true_expr: ir.Value, false_expr: ir.Value, /) -> ir.Value:
        raise NotImplementedError
