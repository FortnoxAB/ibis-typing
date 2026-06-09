"""Types for generated `IbisSchema` definitions.

Note: `bool` subclasses `int` and `datetime` subclasses `date`.
These types are therefore order-sensitive in signature overloads.
"""

from __future__ import annotations

import datetime
import decimal
import functools
import typing
import uuid
from typing import Hashable, Mapping, Sequence, Any
from ibis.expr.datatypes import core
import ibis

# ruff: noqa
__all__ = [
    # Wildcards
    "AnyType",
    "NameOrType",
    "NameOrTypeOrValue",
    # Types
    "Null",
    "Int8",
    "Int16",
    "Int32",
    "Int64",
    "Float32",
    "Float64",
    "Boolean",
    "Integer",
    "Floating",
    "String",
    "Binary",
    "Decimal",
    "Timestamp",
    "Date",
    "Time",
    "UUID",
    "Struct",
    "JSON",
    "Array",
    "Map",
]

# Union types for IbisSchemas

# Null (not-so-important)
type Null = None
# Primitive types (bit-specific)
type Int8 = int | IntegerType | None
type Int16 = int | IntegerType | None
type Int32 = int | IntegerType | None
type Int64 = int | IntegerType | None
type Float32 = float | FloatingType | None
type Float64 = float | FloatingType | None
# Primitive types
type Boolean = bool | BooleanType | None
type Integer = Int8 | Int16 | Int32 | Int64
type Floating = Float32 | Float64
type String = str | StringType | None
type Binary = bytes | BinaryType | None
# Complex types
type Decimal = decimal.Decimal | DecimalType | None
type Timestamp = datetime.datetime | TimestampType | None
type Date = datetime.date | DateType | None
type Time = datetime.time | TimeType | None
type UUID = uuid.UUID | UUIDType | None
# Categories
type Numeric = Integer | Floating | Decimal
type DateCompatible = Timestamp | Date

# Collections
# Note: Collections might have non-hashable signatures,
# in which case type checkers might complain.

# Non-typed collections
type Struct[T] = Mapping[str, Any] | StructType | None
# Collections
type Array[T] = Sequence[T] | ArrayType[T] | None
type Map[K, V] = Mapping[K, V] | MapType[K, V] | None
# Dynamic types
type JSON = JSONType | Any | None

# Wildcards for generic Ibis functions
type NameOrType = str | AnyType
type NameOrTypeOrValue = NameOrType | ibis.ir.Value
type AnyType = (
    # Primitive types
    Boolean
    | Integer
    | Floating
    | String
    | Binary
    # Complex types
    | Decimal
    | Timestamp
    | Date
    | Time
    | UUID
    # Non-typed collections
    | Struct
    | JSON
    # Collections
    | Array
    | Map
)


# Token classes for ibis type patching support.
# fmt: off
# Primitive types
class BooleanType: ...
class IntegerType(int): ...
class FloatingType(float): ...
class StringType(str): ...
class BinaryType(bytes): ...
# Complex types
class DecimalType(decimal.Decimal): ...
class TimestampType(datetime.datetime): ...
class DateType(datetime.date): ...
class TimeType(datetime.time): ...
class UUIDType(uuid.UUID): ...
# Non-typed collections
class StructType(Mapping[str, Any], Hashable): ...
class JSONType: ...
# Collections
class ArrayType[T](Sequence[T], Hashable): ...
class MapType[K, V](Mapping[K, V], Hashable): ...
# fmt: on


type TypeMap[T: AnyType] = Mapping[T, core.DataType]
type TypeConstructorMap[T: AnyType] = Mapping[T, type[core.DataType]]


@functools.lru_cache
def to_ibis_core_type(ibis_type: AnyType) -> core.DataType:
    """Convert an IbisSchema type to an Ibis core type."""

    container_constructors: TypeConstructorMap = {
        Array: core.Array,
        Map: core.Map,
        Struct: core.Struct,
    }
    simple_type_lookup: TypeMap = {
        # Primitive types (bit-specific)
        Int8: core.int8,
        Int16: core.int16,
        Int32: core.int32,
        Int64: core.int64,
        Float32: core.float32,
        Float64: core.float64,
        # Primitive types
        Boolean: core.boolean,
        String: core.string,
        Binary: core.binary,
        # Complex types
        Decimal: core.decimal,
        Timestamp: core.timestamp,
        Date: core.date,
        Time: core.time,
        UUID: core.uuid,
        # Non-typed collections
        JSON: core.json,
    }

    if container_type := typing.get_origin(ibis_type):
        type_params = typing.get_args(ibis_type)
        if container_type is Struct:
            types = {
                name: to_ibis_core_type(type_)
                for name, type_ in typing.get_type_hints(*type_params).items()
            }
            return core.Struct(fields=core.FrozenOrderedDict(types))

        constructor = container_constructors[container_type]
        ibis_types = [to_ibis_core_type(arg) for arg in type_params]
        return constructor(*ibis_types)  # type: ignore

    return simple_type_lookup[ibis_type]
