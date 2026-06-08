from __future__ import annotations

import functools
import operator
from collections.abc import Mapping, Sequence
from typing import Any, Protocol

import attrs
from attrs import frozen


class ExtensionMethod[T, R](Protocol):
    """Class-based implementation of Extension methods via obj @ Method() syntax."""

    def __rmatmul__(self, other: T) -> R: ...


@frozen
class Deferred[I, O](ExtensionMethod[I, O]):
    """Defer attributes and calls for later application.

    Store all attribute accesses and calls for later chained application.
    """

    _chain: Sequence[ExtensionMethod] = ()

    def __rmatmul__(self, other: I) -> O:
        """Apply all deferred calls on `other @ self` invocation.

        >>> 1 @ (Deferred().__add__(2))
        3
        """
        return functools.reduce(operator.matmul, self._chain, other)  # type: ignore

    def __matmul__[R](self, other: ExtensionMethod[O, R]) -> Deferred[I, R]:
        """Append the ExtensionMethod to the call chain.

        >>> Deferred().filter(0, arg=1).values[2]
        Deferred @ .filter(0, arg=1).values[2]
        """
        return attrs.evolve(self, chain=(*self._chain, other))  # type: ignore

    def __call__(self, *args, **kwargs) -> Deferred[I, Any]:
        return self @ Call(args, kwargs)

    def __getattr__(self, name: str) -> Deferred[I, Any]:
        return self @ GetAttr(name)

    def __getitem__(self, item) -> Deferred[I, Any]:
        return self @ GetItem(item)

    def __repr__(self):
        return self.__class__.__name__ + " @ " + "".join(repr(op) for op in self._chain)


@frozen(repr=False)
class Call(ExtensionMethod):
    """Deferred __call__ call."""

    args: tuple
    kwargs: Mapping

    def __rmatmul__(self, other):
        return other(*self.args, **self.kwargs)

    def __repr__(self):
        args = ", ".join(repr(v) for v in self.args)
        kwargs = ", ".join(f"{kw}={arg!r}" for kw, arg in self.kwargs.items())
        return f"({args}{', ' if kwargs else ''}{kwargs})"


@frozen(repr=False)
class GetAttr(ExtensionMethod):
    """Deferred __getattr__ call."""

    name: str

    def __rmatmul__(self, other):
        return getattr(other, self.name)

    def __repr__(self):
        return f".{self.name}"


@frozen(repr=False)
class GetItem(ExtensionMethod):
    """Deferred __getitem__ call."""

    item: Any

    def __rmatmul__(self, other):
        return other[self.item]

    def __repr__(self):
        return f"[{self.item!r}]"
