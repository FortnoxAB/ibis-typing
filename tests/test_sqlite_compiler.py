from __future__ import annotations

import ibis
import pytest
from attrs import frozen

from ibis_typing import IbisSchema, it
from ibis_typing.ibis_connection import IbisConnection


@frozen
class SQLiteSchema(IbisSchema):
    id: it.Int64
    name: it.String


@pytest.fixture
def sqlite_connection() -> IbisConnection:
    return IbisConnection(ibis.sqlite.connect())


@pytest.mark.parametrize(
    "rows",
    [
        [],
        [SQLiteSchema(id=1, name="a"), SQLiteSchema(id=2, name="b")],
    ],
    ids=["empty", "non_empty"],
)
def test_sqlite_literal_table_of_rows(sqlite_connection, rows):
    expected = rows
    actual = list(sqlite_connection.fetch_table(SQLiteSchema.of_rows(rows)))
    assert actual == expected
