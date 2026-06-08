from __future__ import annotations

import functools
from collections.abc import Mapping, Sequence
from typing import Any, Protocol, Self

import attrs
from attrs import frozen


class ExtensionMethod[T, R](Protocol):
    """Class-based implementation of Extension methods via obj @ Method() syntax."""

    def __rmatmul__(self, other: T) -> R: ...


def apply_extension_method[T, R](instance: T, method: ExtensionMethod[T, R]) -> R:
    """Function-interface variant of an extension method for use with `functools`."""
    return instance @ method


@frozen
class Call(ExtensionMethod):
    """Deferred __call__ call."""

    args: tuple
    kwargs: Mapping

    def __rmatmul__(self, other):
        return other(*self.args, **self.kwargs)


@frozen
class GetAttr(ExtensionMethod):
    """Deferred __getattr__ call."""

    name: str

    def __rmatmul__(self, other):
        return getattr(other, self.name)


@frozen
class GetItem(ExtensionMethod):
    """Deferred __getitem__ call."""

    item: Any

    def __rmatmul__(self, other):
        return other[self.item]


@frozen
class Deferred(ExtensionMethod[Any, Any]):
    """Defer attributes and calls for later application.

    Store all attribute accesses and calls for later chained application.
    """

    _chain: Sequence[ExtensionMethod] = ()

    def __rmatmul__(self, other: Any) -> Any:
        """Apply all deferred calls on @ invocation."""
        return functools.reduce(apply_extension_method, self._chain, other)

    def _add_call(self, other: ExtensionMethod) -> Self:
        """Create a new DeferredChain appended with the specified call."""
        return attrs.evolve(self, chain=(*self._chain, other))

    def __call__(self, *args, **kwargs) -> Self:
        return self._add_call(Call(args, kwargs))

    def __getattr__(self, name: str) -> Self:
        return self._add_call(GetAttr(name))

    def __getitem__(self, item) -> Self:
        return self._add_call(GetItem(item))
