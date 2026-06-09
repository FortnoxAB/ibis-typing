from __future__ import annotations

import pytest
from ibis.backends import duckdb

from ibis_typing import IbisConnection


@pytest.fixture
def duck_connection(monkeypatch):
    return IbisDuckConnection()


class IbisDuckConnection(IbisConnection):
    def __init__(self):
        (connection := duckdb.Backend()).do_connect(memory_limit="1GB")
        super().__init__(connection)
