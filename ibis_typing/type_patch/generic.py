# Note: `bool` subclasses `int` and `datetime` subclasses `date.
#  These types are therefore order-sensitive.
# Note: Value defines class method `type()`, so we need to use `typing.Type`.
# ruff: noqa: UP006, UP035
from __future__ import annotations

from types import MethodType
from typing import TYPE_CHECKING, Any, cast, overload

import ibis
from ibis import Column, Scalar, Value, ir

from . import inspect_types
from .patchers import (
    FunctionOverloadPatcher,
    MethodOverloadPatcher,
    MethodSelfReturnTypePatcher,
    TypeCheckingModulePatcher,
)


def get_patchers():
    scalars = inspect_types.get_methods(Column, Scalar)
    values = inspect_types.get_methods(Column, Value)
    columns = inspect_types.get_self_methods(Column)
    column_methods = scalars + values + columns
    value_methods: list[MethodType] = [
        cast(MethodType, Value.coalesce),
        cast(MethodType, Value.nullif),
    ]
    method_self = column_methods + value_methods
    methods = [
        ValueExtensionMethodPatch,
        ValueCast,
        ValueTryCast,
        ValueFillNull,
    ]
    functions = [
        literal,
    ]
    return [
        TypeCheckingModulePatcher(__file__),
        *[MethodOverloadPatcher(patch) for patch in methods],
        *[MethodSelfReturnTypePatcher(method) for method in method_self],
        *[FunctionOverloadPatcher(func) for func in functions],
    ]


class ValueExtensionMethodPatch(Value):
    # Custom patch for adding type support for `it.defer(int).method()`
    # Hi-jack any unpatched function.

    @overload
    def __rmatmul__(self, other: Value) -> Self: ...  # type: ignore

    def name(self, name: str, /) -> Self:
        raise NotImplementedError


class ValueCast(Value):
    # Python types
    # Primitives
    @overload
    def cast(self, target_type: Type[bool]) -> ir.BooleanValue: ...
    @overload
    def cast(self, target_type: Type[int]) -> ir.IntegerValue: ...
    @overload
    def cast(self, target_type: Type[float]) -> ir.FloatingValue: ...
    @overload
    def cast(self, target_type: Type[bytes]) -> ir.BinaryValue: ...
    @overload
    def cast(self, target_type: Type[str]) -> ir.StringValue: ...
    # Complex types
    @overload
    def cast(self, target_type: Type[datetime.datetime]) -> ir.TimestampValue: ...
    @overload
    def cast(self, target_type: Type[datetime.date]) -> ir.DateValue: ...
    @overload
    def cast(self, target_type: Type[datetime.time]) -> ir.TimeValue: ...
    @overload
    def cast(self, target_type: Type[decimal.Decimal]) -> ir.DecimalValue: ...
    @overload
    def cast(self, target_type: Type[uuid.UUID]) -> ir.UUIDValue: ...

    # Ibis data types
    # Primitives
    @overload
    def cast(self, target_type: dt.Boolean) -> ir.BooleanValue: ...
    @overload
    def cast(self, target_type: dt.Integer) -> ir.IntegerValue: ...
    @overload
    def cast(self, target_type: dt.Floating) -> ir.FloatingValue: ...
    @overload
    def cast(self, target_type: dt.Binary) -> ir.BinaryValue: ...
    @overload
    def cast(self, target_type: dt.String) -> ir.StringValue: ...
    # Complex types
    @overload
    def cast(self, target_type: dt.Timestamp) -> ir.TimestampValue: ...
    @overload
    def cast(self, target_type: dt.Date) -> ir.DateValue: ...
    @overload
    def cast(self, target_type: dt.Time) -> ir.TimeValue: ...
    @overload
    def cast(self, target_type: dt.Decimal) -> ir.DecimalValue: ...
    @overload
    def cast(self, target_type: dt.UUID) -> ir.UUIDValue: ...
    # Collections
    @overload
    def cast(self, target_type: dt.Array) -> ir.ArrayValue: ...
    @overload
    def cast(self, target_type: dt.Map) -> ir.MapValue: ...
    # Non-typed collections
    @overload
    def cast(self, target_type: dt.JSON) -> ir.JSONValue: ...
    @overload
    def cast(self, target_type: dt.Struct) -> ir.StructValue: ...
    # Other
    @overload
    def cast(self, target_type: Any) -> Value: ...

    def cast(self, target_type) -> Value:
        raise NotImplementedError


class ValueTryCast(Value):
    # Python types
    # Primitives
    @overload
    def try_cast(self, target_type: Type[bool]) -> ir.BooleanValue: ...
    @overload
    def try_cast(self, target_type: Type[int]) -> ir.IntegerValue: ...
    @overload
    def try_cast(self, target_type: Type[float]) -> ir.FloatingValue: ...
    @overload
    def try_cast(self, target_type: Type[bytes]) -> ir.BinaryValue: ...
    @overload
    def try_cast(self, target_type: Type[str]) -> ir.StringValue: ...
    # Complex types
    @overload
    def try_cast(self, target_type: Type[datetime.datetime]) -> ir.TimestampValue: ...
    @overload
    def try_cast(self, target_type: Type[datetime.date]) -> ir.DateValue: ...
    @overload
    def try_cast(self, target_type: Type[datetime.time]) -> ir.TimeValue: ...
    @overload
    def try_cast(self, target_type: Type[decimal.Decimal]) -> ir.DecimalValue: ...
    @overload
    def try_cast(self, target_type: Type[uuid.UUID]) -> ir.UUIDValue: ...

    # Ibis data types
    # Primitives
    @overload
    def try_cast(self, target_type: dt.Boolean) -> ir.BooleanValue: ...
    @overload
    def try_cast(self, target_type: dt.Integer) -> ir.IntegerValue: ...
    @overload
    def try_cast(self, target_type: dt.Floating) -> ir.FloatingValue: ...
    @overload
    def try_cast(self, target_type: dt.Binary) -> ir.BinaryValue: ...
    @overload
    def try_cast(self, target_type: dt.String) -> ir.StringValue: ...
    # Complex types
    @overload
    def try_cast(self, target_type: dt.Timestamp) -> ir.TimestampValue: ...
    @overload
    def try_cast(self, target_type: dt.Date) -> ir.DateValue: ...
    @overload
    def try_cast(self, target_type: dt.Time) -> ir.TimeValue: ...
    @overload
    def try_cast(self, target_type: dt.Decimal) -> ir.DecimalValue: ...
    @overload
    def try_cast(self, target_type: dt.UUID) -> ir.UUIDValue: ...
    # Collections
    @overload
    def try_cast(self, target_type: dt.Array) -> ir.ArrayValue: ...
    @overload
    def try_cast(self, target_type: dt.Map) -> ir.MapValue: ...
    # Non-typed collections
    @overload
    def try_cast(self, target_type: dt.JSON) -> ir.JSONValue: ...
    @overload
    def try_cast(self, target_type: dt.Struct) -> ir.StructValue: ...
    # Other
    @overload
    def try_cast(self, target_type: Any) -> Value: ...

    def try_cast(self, target_type) -> Value:
        raise NotImplementedError


class ValueFillNull(Value):
    @overload
    def fill_null(self, fill_value: Scalar) -> Self: ...
    @overload
    def fill_null(self, fill_value: Value) -> Self: ...
    def fill_null(self, fill_value) -> Value:
        raise NotImplementedError


@overload
def literal(value: None) -> ir.NullValue: ...
# Primitives
@overload
def literal(value: bool | None) -> ir.BooleanValue: ...
@overload
def literal(value: int | None) -> ir.IntegerValue: ...
@overload
def literal(value: float | None) -> ir.FloatingValue: ...
@overload
def literal(value: str | None) -> ir.StringValue: ...
@overload
def literal(value: bytes | None) -> ir.BinaryValue: ...
# Complex types
@overload
def literal(value: datetime.datetime | None) -> ir.TimestampValue: ...
@overload
def literal(value: datetime.date | None) -> ir.DateValue: ...
@overload
def literal(value: datetime.time | None) -> ir.TimeValue: ...
@overload
def literal(value: decimal.Decimal | None) -> ir.DecimalValue: ...
# Other
@overload
def literal(value: Any) -> ir.Value: ...
@overload
def literal(value: Any, type: Any | None = None) -> ir.Value: ...
def literal(value, type=None):
    return ibis.literal(value, type=type)


if TYPE_CHECKING:
    import datetime
    import decimal
    import uuid
    from typing import Self, Type

    from ibis_typing import dt
