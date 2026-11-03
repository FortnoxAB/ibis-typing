"""Patched ibis backend signatures accept a `(catalog, database)` tuple.

The calls below are checked statically against the patched ibis modules and at
runtime against the real signatures through `mock.create_autospec`.
"""

from unittest import mock

import ibis
from ibis.backends import BaseBackend
from ibis.backends.sql import SQLBackend
from ibis.backends.trino import Backend as TrinoBackend

NAMESPACE = ("catalog", "schema")


def test_base_backend_table_and_view_operations_accept_a_namespace_tuple():
    mocked = mock.create_autospec(BaseBackend, instance=True)
    backend: BaseBackend = mocked
    table = ibis.memtable({"a": [1]})

    backend.create_table("t", table, database=NAMESPACE)
    backend.drop_table("t", database=NAMESPACE)
    backend.create_view("v", table, database=NAMESPACE)
    backend.drop_view("v", database=NAMESPACE)

    assert mocked.mock_calls == [
        mock.call.create_table("t", table, database=NAMESPACE),
        mock.call.drop_table("t", database=NAMESPACE),
        mock.call.create_view("v", table, database=NAMESPACE),
        mock.call.drop_view("v", database=NAMESPACE),
    ]


def test_sql_backend_view_and_row_operations_accept_a_namespace_tuple():
    mocked = mock.create_autospec(SQLBackend, instance=True)
    backend: SQLBackend = mocked
    table = ibis.memtable({"a": [1]})

    backend.create_view("v", table, database=NAMESPACE)
    backend.drop_view("v", database=NAMESPACE)
    backend.insert("t", table, database=NAMESPACE)
    backend.upsert("t", table, "a", database=NAMESPACE)

    assert mocked.mock_calls == [
        mock.call.create_view("v", table, database=NAMESPACE),
        mock.call.drop_view("v", database=NAMESPACE),
        mock.call.insert("t", table, database=NAMESPACE),
        mock.call.upsert("t", table, "a", database=NAMESPACE),
    ]


def test_trino_backend_create_table_accepts_a_namespace_tuple():
    mocked = mock.create_autospec(TrinoBackend, instance=True)
    backend: TrinoBackend = mocked
    table = ibis.memtable({"a": [1]})

    backend.create_table("t", table, database=NAMESPACE)

    assert mocked.mock_calls == [mock.call.create_table("t", table, database=NAMESPACE)]
