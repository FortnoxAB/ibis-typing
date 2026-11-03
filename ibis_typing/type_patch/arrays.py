"""Type patches for ibis arrays.

ibis arrays carry no element type, so `ArrayValue.map` and `filter` declare
their callbacks over `ir.Value`. Callbacks written for the element type, such as
`JsonFormat().apply`, are then rejected. Accept callbacks over any value type.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, overload

from ibis import ir

from .patchers import (
    MethodOverloadPatcher,
    TypeCheckingModulePatcher,
    TypingOverloadImportPatcher,
)


def get_patchers():
    return [
        TypingOverloadImportPatcher(),
        TypeCheckingModulePatcher(__file__),
        MethodOverloadPatcher(ArrayValueMap),
        MethodOverloadPatcher(ArrayValueFilter),
    ]


class ArrayValueMap(ir.ArrayValue):
    @overload
    def map(self, func: Deferred, /) -> ir.ArrayValue: ...
    @overload
    def map(self, func: Callable[[Any], ir.Value], /) -> ir.ArrayValue: ...
    @overload
    def map(self, func: Callable[[Any, Any], ir.Value], /) -> ir.ArrayValue: ...
    def map(self, func: Any, /) -> ir.ArrayValue:
        raise NotImplementedError


class ArrayValueFilter(ir.ArrayValue):
    @overload
    def filter(self, predicate: Deferred, /) -> ir.ArrayValue: ...
    @overload
    def filter(
        self, predicate: Callable[[Any], bool | ir.BooleanValue], /
    ) -> ir.ArrayValue: ...
    @overload
    def filter(
        self, predicate: Callable[[Any, Any], bool | ir.BooleanValue], /
    ) -> ir.ArrayValue: ...
    def filter(self, predicate: Any, /) -> ir.ArrayValue:
        raise NotImplementedError


if TYPE_CHECKING:
    from collections.abc import Callable

    from ibis.common.deferred import Deferred
