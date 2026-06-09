from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Protocol, cast

import ibis
from attrs import frozen
from ibis import Table, Value, ir, literal
from ibis.expr import datatypes as dt

from ibis_typing.ibis_extension_method import TableMethod

from . import ibis_types as it
from . import this


class DefaultProvider(Protocol):
    def __call__(self, col: Value | dt.DataType) -> Value | None: ...


@frozen
class Defaults(DefaultProvider):
    defaults: Mapping[type[dt.DataType], Value]
    default_providers: Sequence[DefaultProvider] = ()
    array_length: ir.IntegerValue | int | None = None

    def __call__(self, col: Value | dt.DataType) -> Value | None:
        data_type = col.type() if isinstance(col, Value) else col

        for type_, default in self.defaults.items():
            if isinstance(data_type, type_):
                return default

        for provider in self.default_providers:
            if (default := provider(col)) is not None:
                return default

        if self.array_length is not None and isinstance(data_type, dt.Array):
            value_type = cast(dt.DataType, data_type.value_type)
            return ibis.array([self(value_type)]) * self.array_length

        return None


numeric_default_provider = Defaults({dt.Numeric: literal(0)})
numeric_or_bool_default_provider = Defaults(
    {dt.Numeric: literal(0), dt.Boolean: literal(False)}
)


@frozen(init=False)
class FillNulls(TableMethod):
    names: Sequence[it.NameOrType]
    default_provider: DefaultProvider = numeric_or_bool_default_provider

    def apply(self, table):
        return fill_nulls(table, *self.names, default_provider=self.default_provider)

    def __init__(
        self,
        *names: it.NameOrType,
        default_provider: DefaultProvider = numeric_or_bool_default_provider,
    ):
        self.__attrs_init__(names, default_provider)  # type: ignore


default_provider: DefaultProvider = numeric_or_bool_default_provider


def fill_nulls(
    table: Table,
    *names: it.NameOrType,
    default_provider: DefaultProvider = numeric_or_bool_default_provider,
    array_length: ir.IntegerValue | int | None = None,
) -> Table:
    names = names or table.columns
    default_provider = (
        default_provider
        if array_length is None
        else Defaults({}, [default_provider], array_length)
    )

    return table.mutate(
        **{
            cast(str, col): this[col].fill_null(default)
            for col in names
            if (default := default_provider(table[col])) is not None
        }
    )
