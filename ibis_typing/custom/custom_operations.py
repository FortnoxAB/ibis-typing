"""Custom Ibis operations provided by ibis-typing."""

from collections.abc import Iterable
from typing import Any, Self

import ibis
from attrs import frozen
from ibis import Schema
from ibis.common.collections import FrozenOrderedDict
from ibis.common.deferred import deferrable
from ibis.expr import datatypes as dt
from ibis.expr.operations import (
    Binary,
    Reduction,
    Relation,
    Unary,
    Value,
)
from ibis.expr.operations.reductions import Filterable


@deferrable
class DateAddMonth(Binary):
    """Specialized DateAdd function inspired by the ordinary DateAdd function."""

    left: Value[dt.Date]
    right: Value[dt.Integer]

    @property
    def dtype(self):
        return dt.date


@deferrable
class DateAddDay(Binary):
    """Specialized DateAdd function inspired by the ordinary DateAdd function."""

    left: Value[dt.Date]
    right: Value[dt.Integer]

    @property
    def dtype(self):
        return dt.date


@deferrable
class ColumnChecksum(Filterable, Reduction):
    arg: Value

    @property
    def dtype(self):
        return dt.int64


@deferrable
class JsonParse(Unary):
    arg: Value[Any]

    @property
    def dtype(self):
        return dt.json


@deferrable
class JsonFormat(Unary):
    """Format a json object as a string"""

    arg: Value

    @property
    def dtype(self):
        return dt.string


@deferrable
class UUIDFromInt(Unary):
    """Conver an int to UUID"""

    arg: Value[dt.Integer]

    @property
    def dtype(self):
        return dt.uuid


@deferrable
class LuhnCheck(Unary):
    """Validate a string using the Luhn algorithm (e.g., credit card numbers, personal identification numbers...)."""

    arg: Value[dt.String]

    @property
    def dtype(self):
        return dt.boolean


class LiteralTable(Relation):
    """A table whose data is represented as plain SQL values.

    Note: Does not support Struct values.
    """

    data: tuple[tuple, ...]

    schema: Schema
    name: str

    @property
    def values(self):
        return FrozenOrderedDict()

    @classmethod
    def from_rows(cls, rows: Iterable, schema: ibis.Schema, name: str) -> Self:
        data = tuple(tuple(cls.literal(val) for val in row) for row in rows)
        return cls(data=data, schema=schema, name=name)

    @classmethod
    def to_values(cls, data) -> tuple[tuple, ...]:
        return tuple(tuple(cls.from_literal(val) for val in row) for row in data)

    @classmethod
    def literal(cls, val: Any) -> Any:
        match val:
            case list():
                return _Array(tuple(cls.literal(val) for val in val))
            case dict():
                return _Map(
                    tuple((cls.literal(k), cls.literal(v)) for k, v in val.items())
                )
            case _:
                return val

    @classmethod
    def from_literal(cls, val: Any) -> Any:
        match val:
            case _Array():
                return [cls.from_literal(v) for v in val.values]
            case _Map():
                return {
                    cls.from_literal(k): cls.from_literal(v) for k, v in val.entries
                }
            case _:
                return val


@frozen
class _Array:
    values: tuple[Any, ...]


@frozen
class _Map:
    entries: tuple[tuple[Any, Any], ...]
