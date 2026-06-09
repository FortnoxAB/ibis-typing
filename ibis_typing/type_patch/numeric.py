from __future__ import annotations

from types import MethodType
from typing import TYPE_CHECKING

from ibis.expr.types.numeric import NumericColumn, NumericScalar, NumericValue

from . import inspect_types
from .patchers import (
    MethodSelfReturnTypePatcher,
    TypeCheckingModulePatcher,
)


def get_patchers():
    value_selfs = inspect_types.get_self_methods(NumericValue)
    value_specifics: list[MethodType] = [  # type: ignore
        NumericValue.ceil,
        NumericValue.floor,
    ]
    column_selfs = inspect_types.get_self_methods(NumericColumn)
    column_scalars = inspect_types.get_methods(NumericColumn, NumericScalar)
    self_methods = value_selfs + value_specifics + column_selfs + column_scalars
    return [
        TypeCheckingModulePatcher(__file__),
        *[MethodSelfReturnTypePatcher(method) for method in self_methods],
    ]


if TYPE_CHECKING:
    from typing import Self

    _ = Self
