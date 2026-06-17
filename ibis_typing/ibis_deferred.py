from __future__ import annotations

import datetime
import decimal
import uuid
from typing import Any, cast, overload

from ibis import Table, Value, ir

from . import ibis_types as it
from .extension_method import Deferred

# Typed token for chaining instance methods after extension methods.
deferred = cast(Table, Deferred())
defer_val = cast(Value, Deferred())


# Ibis value types
@overload
def defer[T: ir.Value](type_: type[T]) -> T: ...
# Primitives
@overload
def defer(type_: type[bool]) -> ir.BooleanValue: ...
@overload
def defer(type_: type[int]) -> ir.IntegerValue: ...
@overload
def defer(type_: type[float]) -> ir.FloatingValue: ...
@overload
def defer(type_: type[bytes]) -> ir.BinaryValue: ...
@overload
def defer(type_: type[str]) -> ir.StringValue: ...
# Complex types
@overload
def defer(type_: type[datetime.datetime]) -> ir.TimestampValue: ...
@overload
def defer(type_: type[datetime.date]) -> ir.DateValue: ...
@overload
def defer(type_: type[datetime.time]) -> ir.TimeValue: ...
@overload
def defer(type_: type[decimal.Decimal]) -> ir.DecimalValue: ...
@overload
def defer(type_: type[uuid.UUID]) -> ir.UUIDValue: ...
# Collection types
@overload
def defer(type_: type[dict]) -> ir.MapValue: ...
@overload
def defer(type_: type[list]) -> ir.ArrayValue: ...
@overload
def defer(type_: type[it.Struct]) -> ir.StructValue: ...
# JSON wildcard
@overload
def defer(type_: type[it.JSON]) -> ir.JSONValue: ...
@overload
def defer(type_: Any = None) -> ir.Value: ...
def defer(type_=None):
    return Deferred()
