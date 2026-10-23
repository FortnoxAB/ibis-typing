"""Non-ibis utility functions."""

from __future__ import annotations

import datetime as _dt
import hashlib
from collections import UserDict
from collections.abc import Callable, Iterable, Mapping, MutableMapping
from types import MethodType
from typing import Any, Self, cast, override

from attrs import frozen


def short_hash(obj: Any, length: int = 8) -> str:
    """Return a short hash of an object as a hex string.

    >>> short_hash("hello")
    'aaf4c61d'
    """
    return hashlib.sha1(str(obj).encode()).hexdigest()[:length]


class StrDate(str):
    """Simple string-compatible date for easy SQL compatible testing.

    >>> d = StrDate("2020-04-02")
    >>> d
    '2020-04-02'
    >>> d == _dt.datetime(2020, 4, 2, 0, 0)
    True
    >>> d == _dt.datetime(2020, 1, 1, 0, 0)
    False
    >>> {d}
    {'2020-04-02'}
    >>> d.datetime
    datetime.datetime(2020, 4, 2, 0, 0)
    >>> d.plus(40)
    '2020-05-12'
    >>> d.minus(10)
    '2020-03-23'
    >>> d.since(d.minus(10))
    10
    >>> d.month_start
    '2020-04-01'
    >>> StrDate("2020-01-31").plus_months(1)
    '2020-02-01'
    >>> StrDate("2020-01-31").plus_months(-1)
    '2019-12-01'
    >>> StrDate("2020-01-31").plus_months(25)
    '2022-02-01'
    >>> StrDate("2020-01-31").plus_months(-25)
    '2017-12-01'
    >>> StrDate("2020-01-31").diff_months(StrDate("2019-01-30"))
    12
    >>> StrDate("2020-01-31").diff_months(StrDate("2021-01-30"))
    -12
    """

    @classmethod
    def now(cls) -> Self:
        return cls(str(_dt.date.today()))

    @property
    def date(self) -> _dt.date:
        return self.datetime.date()

    @property
    def time(self) -> _dt.time:
        return self.datetime.time()

    @property
    def datetime(self) -> _dt.datetime:
        return _dt.datetime.fromisoformat(str(self))

    @property
    def posix_timestamp(self) -> int:
        return int(self.datetime.timestamp())

    def plus(self, days: int) -> Self:
        new = self.datetime + _dt.timedelta(days=int(days))
        return type(self)(str(new.date()))

    def plus_months(self, months: int) -> Self:
        month_tot = self.date.month - 1 + months
        year_add = month_tot // 12
        month_index = month_tot % 12

        year = self.date.year + year_add
        month = month_index + 1
        return type(self)(str(_dt.date(year, month, 1)))

    def diff_months(self, date: StrDate) -> int:
        diff_year = self.date.year - date.date.year
        diff_months = self.date.month - date.date.month
        return diff_year * 12 + diff_months

    def minus(self, days: int) -> Self:
        return self.plus(-days)

    def since(self, other: StrDate) -> int:
        return self.datetime.toordinal() - other.datetime.toordinal()

    @property
    def month_start(self) -> Self:
        return type(self)(self.datetime.replace(day=1).date())

    @override
    def __eq__(self, other: object) -> bool:
        match other:
            case StrDate():
                return self.datetime == other.datetime
            case _dt.date():
                return self == type(self)(str(other))
            case _:
                return NotImplemented

    def __hash__(self):
        return super().__hash__()


def group_by[T, K](
    iterable: Iterable[T], *, key: Callable[[T], K], drop_none_keys: bool = False
) -> dict[K, list[T]]:
    """Group iterable by a key function, not requiring it to be sorted.

    >>> group_by([1, 2, 3, 4, 5, 6], key=lambda x: x % 2)
    {1: [1, 3, 5], 0: [2, 4, 6]}
    """
    ret = {}
    for value in iterable:
        k = key(value)
        if k is None and drop_none_keys:
            continue

        ret.setdefault(k, []).append(value)

    return ret


type MapByType[T] = MutableMapping[type[T], list[T]]


def group_by_type[T](iterable: Iterable[T]) -> MapByType[T]:
    return group_by(iterable, key=lambda entry: entry.__class__)


class BoxedDict(UserDict[str, str], Mapping[str, str]):
    """A dictionary that allows attribute access to its keys.

    >>> d = BoxedDict({"a": "b"})
    >>> d.a
    'b'
    """

    def __getattr__(self, item: str) -> str:
        try:
            return self[item]
        except LookupError as e:
            raise AttributeError(*e.args)


@frozen(eq=False)
class ApproxFloat(float):  # noqa: PLW1641
    """An approximate float representation with specific tolerance.

    Implements equality check with geometric (semi-square) error tolerance.

    >>> ApproxFloat(1) == 1
    True
    >>> ApproxFloat(1) == 0
    False
    >>> ApproxFloat(1) == 0.95
    False
    >>> ApproxFloat(1) == 0.96
    True
    >>> ApproxFloat(1) == 1.05
    True
    >>> ApproxFloat(1) == 1.06
    False
    """

    number: float

    e: float = 0.05  # > 0
    abs_e: float = 0.001  # > 0

    @override
    def __eq__(self, other: Any) -> bool:
        numerator = (self.number - other) ** 2  # > 0
        denominator = abs(self.number * other) or self.abs_e**2  # > 0
        threshold = self.e**2
        return numerator / denominator < threshold


def classproperty[R](class_method: Callable[..., R]) -> R:
    """Simple class property decorator.

    Note: JetBrains type tooling does not support @classproperty decorator syntax.

    >>> class DynamicProperty:
    ...     @classmethod
    ...     def get_prop(cls) -> int:
    ...         return 1
    ...
    ...     prop = classproperty(get_prop)

    >>> DynamicProperty.prop
    1

    >>> class MyOverride(DynamicProperty):
    ...     @classmethod
    ...     def get_prop(cls) -> int:
    ...         return 2

    >>> MyOverride.prop
    2

    >>> class MySubclass(MyOverride):
    ...     pass

    >>> MySubclass.prop
    2

    >>> class DecoratorProperty:
    ...     @classproperty
    ...     @classmethod
    ...     def prop(cls) -> int:
    ...         return 1

    >>> DecoratorProperty.prop
    1
    """
    return cast(R, _ClassProperty(class_method))


@frozen
class _ClassProperty[R]:
    class_method: Callable[..., R]

    def __get__(self, instance: None, owner: type) -> R:
        name = getattr(self.class_method, "__name__")
        impl = next(impl for cls in owner.__mro__ if (impl := vars(cls).get(name)))
        func = impl if impl is not self else self.class_method
        return cast(MethodType, func).__func__(owner)
