"""Time operations for `ibis.Table` expressions."""

from __future__ import annotations

import datetime
from typing import Self, cast

import ibis
from attrs import frozen
from ibis import ir, literal
from ibis.expr import datatypes as dt
from typing_extensions import deprecated

from . import ibis_types as it
from .custom.custom_operations import DateAddDay, DateAddMonth
from .custom.op_cast import op_cast
from .expression import Expression
from .ibis_adapter import IbisTable
from .ibis_extension_method import ValueMethod


@frozen
class TimestampNow(Expression):
    """Table with current timestamp used for functional programming."""

    timestamp: it.Timestamp = None

    table_schema = {  # noqa: RUF012
        "timestamp": "timestamp(6)",
    }

    @classmethod
    def from_expression(cls):
        return cls.as_of()

    @classmethod
    def as_of(cls, timestamp: datetime.datetime | None = None) -> IbisTable[Self]:
        if timestamp:
            return cls.of_rows([cls(timestamp)])
        table = cls.of_rows([cls()]).table
        table = table.mutate(**{str(cls.cols.timestamp): now()})
        return cls.of(table)

    @classmethod
    def as_scalar(cls, table: IbisTable[Self]) -> ibis.ir.TimestampScalar:
        scalar = table.table[cls.cols.timestamp].as_scalar()
        return cast(ibis.ir.TimestampScalar, scalar)


@frozen
class StartOfMonth(ValueMethod[ir.DateValue, ir.DateValue]):
    def apply(self, value: ir.DateValue):
        return value.truncate("M")


@frozen
class MonthsSince(ValueMethod[ir.DateValue, ir.IntegerValue]):
    start: ir.DateValue | datetime.date

    def apply(self, value: ir.DateValue):
        return value.delta(_coerce_date(self.start), unit="month")


@frozen
class DaysSince(ValueMethod[ir.DateValue, ir.IntegerValue]):
    start: ir.DateValue | datetime.date

    def apply(self, value: ir.DateValue):
        return value.delta(_coerce_date(self.start), unit="day")


@frozen
class AddMonths(ValueMethod[ir.DateValue, ir.DateValue]):
    """Add months to a date, returning a new date at start of month.

    Note: Work-around for Ibis using `datetime.date`
    which only supports fixed-length intervals, that is, not months.
    """

    months: ir.IntegerValue | int

    def apply(self, value: ir.DateValue):
        return DateAddMonth(
            op_cast(value @ StartOfMonth()), op_cast(_coerce_int(self.months))
        ).to_expr()


@frozen
class AddDays(ValueMethod[ir.DateValue, ir.DateValue]):
    days: ir.IntegerValue | int

    def apply(self, value: ir.DateValue):
        return DateAddDay(
            op_cast(value), op_cast(_coerce_int(self.days).cast(dt.int32))
        ).to_expr()


def now() -> ir.TimestampValue:
    """Get current timestamp.

    Can be mocked by test fixture.
    For functional programming, use NowTimestamp as a table input.
    """
    timestamp = ibis.now().cast("timestamp(6)")
    return cast(ir.TimestampValue, timestamp)


def _coerce_date(d: ir.DateValue | datetime.date) -> ir.DateValue:
    if isinstance(d, datetime.date):
        return literal(d)
    return d


def _coerce_int(n: ir.IntegerValue | int) -> ir.IntegerValue:
    if isinstance(n, int):
        return literal(n)
    return n


@deprecated("Use `date @ StartOfMonth()`")
def truncate_month(date: ir.DateValue) -> ir.DateValue:
    return date @ StartOfMonth()


@deprecated("Use `end @ MonthsSince()`")
def diff_months(
    end: ir.DateValue, start: ir.DateValue | datetime.date
) -> ir.IntegerValue:
    return end @ MonthsSince(start)


@deprecated("Use `end @ DaysSince()`")
def diff_days(
    end: ir.DateValue, start: ir.DateValue | datetime.date
) -> ir.IntegerValue:
    return end @ DaysSince(start)


@deprecated("Use `date @ AddMonths()`")
def add_months(date: ir.DateValue, months: ir.IntegerValue | int) -> ir.DateValue:
    return date @ AddMonths(months)


@deprecated("Use `date @ AddDays()`")
def add_days(date: ir.DateValue, days: ir.IntegerValue | int) -> ir.DateValue:
    return date @ AddDays(days)
