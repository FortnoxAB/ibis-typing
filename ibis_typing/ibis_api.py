"""ValueMethod variants of ibis.api functions."""

from collections.abc import Sequence

import ibis
from attrs import frozen
from ibis import Value, ir

from ibis_typing.ibis_extension_method import ArgsMethod, SelfMethod, ValueMethod


@frozen
class Desc[T: Value](SelfMethod[T]):
    nulls_first: bool = False

    def apply(self, value: T):
        return ibis.desc(value, nulls_first=self.nulls_first)


@frozen
class IfElse[T: Value](ValueMethod[ir.BooleanValue, T]):
    left: T
    right: T

    def apply(self, value: ir.BooleanValue):
        return ibis.ifelse(value, self.left, self.right)


@frozen(init=False)
class Cases[T: Value](SelfMethod[T]):
    args: Sequence[tuple[ir.BooleanValue, T]]

    def __init__(self, *args: tuple[ir.BooleanValue, T]):
        self.__attrs_init__(args)  # type: ignore

    def apply(self, value: T):
        return ibis.cases(*self.args, else_=value)


class FillNull[T: Value](ArgsMethod[T]):
    def apply(self, value: T):
        return ibis.coalesce(value, *self.args)


class Greatest[T: Value](ArgsMethod[T]):
    def apply(self, value: T):
        return ibis.greatest(value, *self.args)


class Least[T: Value](ArgsMethod[T]):
    def apply(self, value: T):
        return ibis.least(value, *self.args)


class And(ArgsMethod[ir.BooleanValue]):
    def apply(self, value: ir.BooleanValue):
        return ibis.and_(value, *self.args)


class Or(ArgsMethod[ir.BooleanValue]):
    def apply(self, value: ir.BooleanValue):
        return ibis.or_(value, *self.args)
