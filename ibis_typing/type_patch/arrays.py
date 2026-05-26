from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any, TypeAliasType, cast, overload

from ibis import Value, ir
from ibis.expr.types import ArrayColumn, ArrayValue

from . import inspect_types
from .patchers import (
    MethodOverloadPatcher,
    MethodSelfReturnTypePatcher,
    TypeCheckingModulePatcher,
    TypingOverloadImportPatcher,
    ValueTypeParameterPatcher,
)

type V = Value
_v = cast(list[TypeAliasType], [V])


def get_patchers():
    # Note: ArrayColumn duplicates ArrayValues for methods with parametric return value.
    methods = [
        ArrayColumnGetItem,
        ArrayValueFilter,
        ArrayValueGetItem,
        ArrayValueMap,
    ]

    self_methods = inspect_types.get_methods(ArrayValue, ArrayValue)
    return [
        TypeCheckingModulePatcher(__file__),
        TypingOverloadImportPatcher(),
        *(MethodSelfReturnTypePatcher(method) for method in self_methods),
        *(MethodOverloadPatcher(patch) for patch in methods),
        ValueTypeParameterPatcher(ArrayValue, _v),
        ValueTypeParameterPatcher(ir.ArrayColumn, _v, base=ArrayValue),
    ]


class ArrayValueMap(ArrayValue):
    type MapUnary[R: Value] = Callable[[V], R]
    type MapBinary[R: Value] = Callable[[V, ir.IntegerValue], R]

    @overload
    def map[R: Value](self, func: MapUnary[R], /) -> ArrayValue[R]: ...
    @overload
    def map[R: Value](self, func: MapBinary[R], /) -> ArrayValue[R]: ...

    def map(self, func) -> ArrayValue:  # ty:ignore[invalid-method-override]
        raise NotImplementedError


class ArrayValueFilter(ArrayValue):
    type FilterUnary = Callable[[V], ir.BooleanValue]
    type FilterBinary = Callable[[V, ir.IntegerValue], ir.BooleanValue]

    @overload
    def filter(self, func: FilterUnary, /) -> Self: ...
    @overload
    def filter(self, func: FilterBinary, /) -> Self: ...

    def filter(self, func) -> Self:  # ty:ignore[invalid-method-override]
        raise NotImplementedError


class ArrayValueGetItem(ArrayValue):
    @overload
    def __getitem__(self, index: int | ir.IntegerValue) -> V: ...
    @overload
    def __getitem__(self, index: slice) -> Self: ...

    def __getitem__(self, index) -> Value:
        raise NotImplementedError


class ArrayColumnGetItem(ArrayColumn):
    @overload
    def __getitem__(self, index: int | ir.IntegerValue) -> V | ir.Column: ...
    @overload
    def __getitem__(self, index: slice) -> Self: ...

    def __getitem__(self, index: Any) -> V | ir.Column:
        raise NotImplementedError


if TYPE_CHECKING:
    from typing import Self
