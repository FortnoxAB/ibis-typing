from __future__ import annotations

from collections import UserString
from collections.abc import Callable
from types import MethodType, ModuleType
from typing import Any, Concatenate, Self, cast
from unittest import mock


class PatchTarget(UserString):
    """Typed symbolic references for `monkeypatch` and `mock.patch`.

    Get a dot-path reference to a static object.

    >>> target = PatchTarget.of(PatchTarget)
    >>> target
    'ibis_typing.fixtures.patch_target.PatchTarget'

    Get a `mock.call()` invocation for comparing calls to mocked objects.

    >>> from unittest import mock
    >>> with mock.patch(target) as mocked_target:
    ...     # <exercise some code interacting with mocked_target>
    ...     _ = mocked_target("mocked_call_arg")
    >>> assert mocked_target.mock_calls == [target("mocked_call_arg")]
    """

    @classmethod
    def of[T](cls, target: T) -> T | Self:
        if isinstance(target, ModuleType):
            return cls(target.__name__)
        return cls(target.__module__, getattr(target, "__qualname__"))

    @classmethod
    def of_instance[T](cls, target: type[T]) -> T | Self:
        return cast(Self, cls.of(target))

    def __init__(self, *attr_chain: str):
        super().__init__(".".join(attr_chain))

    def __getattr__(self, attr):
        return PatchTarget(str(self), attr)

    def __call__(self, *args, **kwargs):
        return mock.call(*args, **kwargs)

    @property
    def __class__(self):
        return str


def classmethod_patch[**P, R](method: Callable[P, R]) -> Callable[P, R]:
    fixed = classmethod(method_func(method))  # type: ignore
    return cast(Any, fixed)


def method_func[**P, R](
    method: Callable[P, R],
) -> Callable[Concatenate[object | type, P], R]:
    """Get a method's function with signature including `self` or `cls`."""
    return cast(MethodType, method).__func__
