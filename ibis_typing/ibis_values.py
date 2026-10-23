"""Provides typed `ibis.Value` operations composed of ibis functions."""

from __future__ import annotations

import ibis
from attrs import frozen
from ibis import Value, ir

from .ibis_extension_method import SelfMethod

__all__ = ["NullUnless"]


@frozen
class NullUnless[T: Value](SelfMethod[T]):
    """`value` where `condition` holds, otherwise null of the same type."""

    condition: ir.BooleanValue

    def apply(self, value: T):
        null = ibis.null(value.type())
        return ibis.ifelse(self.condition, value, null)
