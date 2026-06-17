from __future__ import annotations

from typing import Any, overload

from _pytest.monkeypatch import MonkeyPatch

from .patchers import MethodOverloadPatcher


def get_patchers():
    methods = [
        SetAttr,
        DelAttr,
    ]
    return [
        *[MethodOverloadPatcher(patch) for patch in methods],
    ]


class SetAttr(MonkeyPatch):  # type: ignore
    @overload
    def setattr(  # type: ignore
        self,
        target: Any,
        name: object,
        value=...,
        raising: bool = True,
    ) -> None: ...

    def setattr(
        self,
        target: str | object,
        name: object | str,
        value: object = ...,
        raising: bool = True,
    ) -> None: ...


class DelAttr(MonkeyPatch):  # type: ignore
    @overload
    def delattr(  # type: ignore
        self,
        target: Any,
        name=...,
        raising: bool = True,
    ) -> None: ...

    def delattr(
        self,
        target: object | str,
        name=...,
        raising: bool = True,
    ) -> None: ...
