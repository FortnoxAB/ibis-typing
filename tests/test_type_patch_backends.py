"""Patched ibis backend signatures accept a `(catalog, database)` tuple.

The calls below are checked statically against the patched ibis modules and at
runtime against the real signatures through `mock.create_autospec`.
"""

import functools
import inspect
from types import ModuleType
from unittest import mock

import ibis
import pytest
from ibis.backends import BaseBackend
from ibis.backends.sql import SQLBackend
from ibis.backends.trino import Backend as TrinoBackend

from ibis_typing.type_patch import backends
from ibis_typing.type_patch.patchers import MethodParameterTypePatcher

NAMESPACE = ("catalog", "schema")
WIDENED = "database: tuple[str, str] | str | None"


@pytest.mark.parametrize(
    ["module", "patchers"],
    [
        (ibis.backends, backends.get_base_patchers()),
        (ibis.backends.sql, backends.get_sql_patchers()),
        (ibis.backends.trino, backends.get_trino_patchers()),
    ],
)
def test_backend_patchers_widen_the_installed_module_source(
    module: ModuleType, patchers: list[MethodParameterTypePatcher]
):
    def apply(source: str) -> str:
        return functools.reduce(lambda impl, patch: patch(impl), patchers, source)

    patched = apply(inspect.getsource(module))

    assert patched.count(WIDENED) >= len(patchers)
    assert apply(patched) == patched


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
