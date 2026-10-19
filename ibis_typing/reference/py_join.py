"""Reference python implementation for IbisSchema transforms like join."""

import builtins
from collections.abc import Mapping, Sequence
from typing import Any

import cattrs

from ibis_typing import IbisSchema, it
from ibis_typing.ibis_joins import JoinMethod


def to_schema[T: IbisSchema](table: Sequence[Mapping], cls: type[T]) -> list[T]:
    return [cls(**row) for row in table]


def select(
    table: Sequence[Mapping], *columns: it.NameOrType
) -> list[Mapping[it.NameOrType, Any]]:
    return [{col: row.get(col) for col in columns} for row in table]


def inner_join(
    *tables: Sequence[IbisSchema | Mapping],
    keys: Sequence[it.NameOrType],
    arbitrary: Sequence[it.NameOrType] = (),
    max: Sequence[it.NameOrType] = (),
    min: Sequence[it.NameOrType] = (),
) -> list[Mapping]:
    return join(
        *tables, how=JoinMethod.INNER, keys=keys, arbitrary=arbitrary, max=max, min=min
    )


def left_join(
    *tables: Sequence[IbisSchema | Mapping],
    keys: Sequence[it.NameOrType],
    arbitrary: Sequence[it.NameOrType] = (),
    max: Sequence[it.NameOrType] = (),
    min: Sequence[it.NameOrType] = (),
) -> list[Mapping]:
    return join(
        *tables, how=JoinMethod.OUTER, keys=keys, arbitrary=arbitrary, max=max, min=min
    )


def outer_join(
    *tables: Sequence[IbisSchema | Mapping],
    keys: Sequence[it.NameOrType],
) -> list[Mapping]:
    return join(*tables, how=JoinMethod.OUTER, keys=keys)


def join(
    *tables: Sequence[IbisSchema | Mapping],
    how: JoinMethod,
    keys: Sequence[it.NameOrType],
    arbitrary: Sequence[it.NameOrType] = (),
    max: Sequence[it.NameOrType] = (),
    min: Sequence[it.NameOrType] = (),
) -> list[Mapping]:
    """Join Python mappings Ibis-style.

    Tables are merged via key fields.

    >>> a = [{"id": 1, "a": 1}]
    >>> b = [{"id": 1, "b": 2}, {"id": 2, "b": 3}]

    >>> join(a, b, how=JoinMethod.INNER, keys=["id"])
    [{'id': 1, 'a': 1, 'b': 2}]
    >>> join(a, b, how=JoinMethod.LEFT, keys=["id"])
    [{'id': 1, 'a': 1, 'b': 2}]
    >>> join(a, b, how=JoinMethod.OUTER, keys=["id"])
    [{'id': 1, 'a': 1, 'b': 2}, {'b': 3, 'id': 2}]
    >>> join(b, a, how=JoinMethod.LEFT, keys=["id"])
    [{'id': 1, 'b': 2, 'a': 1}, {'id': 2, 'b': 3}]

    Common fields across tables are suffixed with `_right`
    or can be combined via binary operators.

    >>> c = [{"id": 1, "a": 2}]

    >>> join(a, c, how=JoinMethod.INNER, keys=["id"])
    [{'id': 1, 'a': 1, 'a_right': 2}]
    >>> join(a, c, how=JoinMethod.INNER, keys=["id"], arbitrary=["a"])
    [{'id': 1, 'a': 1}]
    >>> join(a, c, how=JoinMethod.INNER, keys=["id"], max=["a"])
    [{'id': 1, 'a': 2}]
    >>> join(a, c, how=JoinMethod.INNER, keys=["id"], min=["a"])
    [{'id': 1, 'a': 1}]
    """
    if len(tables) == 1:
        return cattrs.unstructure(tables[0])

    t_left, t_right, *tail = tables

    left = _index_by_key(t_left, keys)
    right = _suffix_conflicts(left, _index_by_key(t_right, keys))

    joined_keys = _join_keys(set(left), set(right), how=how)
    joined = [left.get(key, {}) | right.get(key, {}) for key in joined_keys]

    processed = _resolve_duplicate_values(
        joined, keys=keys, arbitrary=arbitrary, max=max, min=min
    )

    return join(
        processed, *tail, how=how, keys=keys, arbitrary=arbitrary, max=max, min=min
    )


def _index_by_key(table: Sequence, keys: Sequence[it.NameOrType]) -> dict[tuple, dict]:
    return {tuple(row[k] for k in keys): row for row in cattrs.unstructure(table)}


def _suffix_conflicts(left: Mapping[tuple, Mapping], right: dict[tuple, dict]) -> dict:
    """Suffix column names of `right` that also exist in `left` with `_right`."""
    left_names = set(next(iter(left.values()), {}).keys())
    right_names = set(next(iter(right.values()), {}).keys())
    conflicts = left_names & right_names

    return {
        key: {
            (f"{name}_right" if name in conflicts else name): value
            for name, value in row.items()
        }
        for key, row in right.items()
    }


def _join_keys(left: set[tuple], right: set[tuple], *, how: JoinMethod) -> set[tuple]:
    match how:
        case JoinMethod.OUTER:
            return left | right
        case JoinMethod.INNER:
            return left & right
        case JoinMethod.LEFT:
            return left
        case _:
            raise ValueError(f"Unsupported join method: {how}")


def _resolve_duplicate_values(
    table: Sequence[Mapping],
    *,
    keys: Sequence[it.NameOrType],
    arbitrary: Sequence[it.NameOrType] = (),
    max: Sequence[it.NameOrType] = (),
    min: Sequence[it.NameOrType] = (),
) -> Sequence[Mapping]:
    override_names = set(keys) | set(arbitrary) | set(max) | set(min)
    drops = {f"{name}_right" for name in override_names}

    groups = [
        ([*keys, *arbitrary], lambda left, _: left),
        (max, builtins.max),
        (min, builtins.min),
    ]
    overrides = [dict(_iter_overrides(row, groups)) for row in table]
    kept = [
        {name: val for name, val in row.items() if name not in drops} for row in table
    ]

    return [row | override for row, override in zip(kept, overrides)]


def _iter_overrides(row: Mapping, groups: Sequence[tuple[Sequence, Any]]):
    for collection, op in groups:
        for name in collection:
            yield name, _binary_op(row.get(name), row.get(f"{name}_right"), op)


def _binary_op(left, right, op):
    match (left, right):
        case (None, _):
            return right
        case (_, None):
            return left
        case _:
            return op(left, right)
