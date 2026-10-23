"""Data generators for the Hypothesis test framework."""

import datetime
import typing
from collections.abc import Mapping, Sequence
from typing import Any

import attrs
from hypothesis import strategies as st

from ibis_typing import IbisSchema, it


@st.composite
def unique[T](draw: st.DrawFn, strategy: st.SearchStrategy[T]) -> T:
    seen = draw(st.shared(st.builds(set), key="key-for-unique-elems"))
    return draw(
        strategy.filter(lambda x: x not in seen).map(lambda x: seen.add(x) or x)
    )


def strategy_for[T: IbisSchema](
    datacls: type[T],
    *,
    # Field names, given as `cols` references typed as their column values.
    kwargs: Mapping[Any, Any] | None = None,
    fields: Sequence[Any] = (),
    uniques: Sequence[Any] = (),
) -> st.SearchStrategy[T]:
    const_kwargs = kwargs or {}
    fields = fields or [
        field.name for field in attrs.fields(datacls) if field.name not in const_kwargs
    ]
    types = typing.get_type_hints(datacls)

    @st.composite
    def strategy(draw: st.DrawFn) -> T:
        strats = {field: ibis_strategies[types[field]] for field in fields}
        kwargs = {
            field: draw(unique(strat) if field in uniques else strat)
            for field, strat in strats.items()
        }
        return datacls(**const_kwargs, **kwargs)

    return strategy()


MIN_DATETIME = datetime.datetime(1970, 1, 1)
MAX_DATETIME = datetime.datetime(2100, 1, 1)

ibis_strategies = {
    # Null (not-so-important)
    it.Null: st.none(),
    # Primitive types (bit-specific)
    **{
        type_: st.integers(min_value=-(2**width), max_value=2**width)
        for type_, width in [
            (it.Int8, 6),
            (it.Int16, 12),
            (it.Int32, 18),
            (it.Int64, 32),
        ]
    },
    **{
        type_: st.integers(min_value=-(2**width), max_value=2**width).map(
            lambda x: x / 2
        )
        for type_, width in [
            (it.Float32, 17),
            (it.Float64, 33),
        ]
    },
    # Primitive types
    it.Boolean: st.booleans(),
    it.String: st.text(
        max_size=2**10,
        alphabet=st.characters(codec="utf-8", blacklist_characters="\x00"),
    ),
    it.Binary: st.binary(max_size=2**10),
    # Complex types
    it.Decimal: st.decimals(
        min_value=-(2**20),
        max_value=2**20,
        places=2,
        allow_nan=False,
        allow_infinity=False,
    ),
    it.Timestamp: st.datetimes(min_value=MIN_DATETIME, max_value=MAX_DATETIME),
    it.Date: st.dates(min_value=MIN_DATETIME.date(), max_value=MAX_DATETIME.date()),
    it.Time: st.times(),
    it.UUID: st.uuids(),
    # Note: The following types have non-obvious accepted values
    # Non-typed collections
    # Collections
}
