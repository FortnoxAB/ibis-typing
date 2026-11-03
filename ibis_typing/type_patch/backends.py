"""Type patches for ibis backends.

ibis routes the `database` argument of table and view operations through
`_to_sqlglot_table`, which takes a `(catalog, database)` tuple as well as a
`"catalog.database"` string, but most public signatures only declare the string.
Widen them to the form ibis already declares for `table` and `list_tables`.
"""

from __future__ import annotations

from types import FunctionType

from ibis.backends import BaseBackend
from ibis.backends.sql import SQLBackend
from ibis.backends.trino import Backend as TrinoBackend

from .patchers import MethodParameterTypePatcher

__all__ = ["get_base_patchers", "get_sql_patchers", "get_trino_patchers"]

_DATABASE = "tuple[str, str] | str | None"


def _accept_database_tuple(*methods: FunctionType):
    return [
        MethodParameterTypePatcher(method, "database", _DATABASE) for method in methods
    ]


def get_base_patchers():
    return _accept_database_tuple(
        BaseBackend.create_table,
        BaseBackend.drop_table,
        BaseBackend.create_view,
        BaseBackend.drop_view,
    )


def get_sql_patchers():
    return _accept_database_tuple(
        SQLBackend.create_view,
        SQLBackend.drop_view,
        SQLBackend.insert,
        SQLBackend.upsert,
    )


def get_trino_patchers():
    return _accept_database_tuple(TrinoBackend.create_table)
