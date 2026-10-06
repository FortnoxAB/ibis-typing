from __future__ import annotations

import ibis
import pytest

from ibis_typing.time_series.features import MeanAbsDiff, MedianFrequency, NUnique, Sum
from tests.time_series.series import extraction, table


def sql(*features, windows: int | tuple[int, ...] = 3) -> str:
    extracted = table([1.0, 2.0, 4.0]) @ extraction(*features, windows=windows)
    return ibis.to_sql(extracted, dialect="duckdb").upper()


def test_window_features_need_no_join():
    assert "JOIN" not in sql(Sum(), MeanAbsDiff())


def test_lag_is_only_computed_for_lag_features():
    assert "LAG(" not in sql(Sum())
    assert "LAG(" in sql(MeanAbsDiff())


def test_spectral_features_expand_each_window():
    assert "JOIN" in sql(MedianFrequency())


def test_joins_grow_linearly_with_the_number_of_windows():
    def joins(windows: tuple[int, ...]) -> int:
        return sql(MedianFrequency(), NUnique(), windows=windows).count("JOIN")

    # Each window is expanded on its own, never from the earlier windows' joins.
    assert joins((3, 4, 5, 6)) <= 2 * joins((3, 4))


@pytest.mark.parametrize("dialect", ("duckdb", "trino"))
def test_sql_size_grows_linearly_with_the_number_of_windows(dialect):
    points = ibis.table(
        {"key": "string", "time": "int64", "a": "float64", "b": "float64"},
        name="points",
    )

    def size(windows: tuple[int, ...]) -> int:
        method = extraction(
            Sum(),
            MeanAbsDiff(),
            NUnique(),
            MedianFrequency(),
            columns=("a", "b"),
            windows=windows,
        )
        return len(ibis.to_sql(points @ method, dialect=dialect))

    # Each window adds its own columns and joins, never a copy of the earlier ones.
    assert size((2, 3, 4, 6, 8, 12, 18, 24)) <= 2.2 * size((3, 6, 12, 24))
