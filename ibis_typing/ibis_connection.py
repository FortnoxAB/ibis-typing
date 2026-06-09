from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

import ibis
from attrs import field, frozen

from . import utils
from .custom import custom_compilers
from .ibis_adapter import IbisSchema, IbisTable
from .ibis_pyarrow import EvaluateExpr, EvaluateIbisTable

custom_compilers.register_operations()


@frozen
class IbisConnection:
    """Database connection adapter with `IbisTable` and `IbisSchema` interface."""

    connection: ibis.BaseBackend = field(factory=ibis.get_backend)

    def fetch_table[T: IbisSchema](self, table: IbisTable[T]) -> Iterable[T]:
        return table @ EvaluateIbisTable(self.connection)

    def evaluate[V](self, expr: ibis.Expr, type_: type[V] | None = None) -> V:
        return expr @ EvaluateExpr(self.connection)

    def read_parquet[S: IbisSchema](
        self, path: Path, /, cls: type[S], **kwargs
    ) -> IbisTable[S]:
        name = f"{cls.__name__}__{utils.short_hash(path.as_posix())}"
        table = self.connection.read_parquet(path, table_name=name, **kwargs)
        table = table.select(*cls.table_schema)
        return cls.of(table)

    def write_parquet(self, table: IbisTable, /, path: Path, **kwargs) -> None:
        self.connection.to_parquet(table.table, path, **kwargs)

    @property
    def dialect(self) -> str:
        """Dialect name of the underlying connection.

        >>> IbisConnection().dialect
        'duckdb'
        """
        return self.connection.name
