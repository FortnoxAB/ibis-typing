"""TableStore implements IbisTable IO, a subclass of TableProvider."""

from __future__ import annotations

import itertools
import logging
import shutil
import tempfile
from abc import ABC, abstractmethod
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Protocol, Self

import attrs
import humanize
import ibis.backends.duckdb
from attrs import frozen
from ibis.expr import operations

from . import (
    IbisConnection,
    IbisSchema,
    IbisTable,
    dt,
    naming,
    utils,
)
from .custom.op_cast import op_cast
from .table_provider import TableProvider

logger = logging.getLogger(__name__)


class TableStore(TableProvider, Protocol):
    def __call__[S: IbisSchema](self, schema: type[S]) -> IbisTable[S] | None:
        """Table Provider."""

    def __contains__(self, schema: type[IbisSchema]) -> bool:
        """Query if table exists in store."""

    def write_table(self, table: IbisTable) -> None:
        """Write table to store."""


@frozen
class NullTableStore(TableStore):
    """/dev/null variant of Table Store."""

    def __call__(self, schema):
        return None

    def __contains__(self, schema):
        return False

    def write_table(self, table) -> None:
        return


@frozen
class LocalTableStore(TableStore, ABC):
    """Table Store backed by local storage."""

    local_path: Path

    @property
    @abstractmethod
    def _file_suffix(self) -> str:
        """File extension for table files of this Table Store, excluding leading dot."""

    @abstractmethod
    def _read_table[S: IbisSchema](self, schema: type[S], glob: Path) -> IbisTable[S]:
        """Implementation of table read for schema file Path glob."""

    @abstractmethod
    def _write_table(self, table: IbisTable, path: Path) -> None:
        """Implementation of table write into schema directory."""

    def __call__(self, schema):
        if schema not in self:
            return None

        glob = self.get_table_path(schema) / self._rglob
        return self._read_table(schema, glob)

    def __contains__(self, schema: type[IbisSchema]) -> bool:
        table_path = self.get_table_path(schema)
        return table_path.is_dir() and bool(list(table_path.glob(self._rglob)))

    @property
    def _rglob(self) -> str:
        return f"**/*.{self._file_suffix}"

    def write_table(self, table: IbisTable) -> None:
        with self.tmp_store() as tmp_store:
            path = tmp_store.get_table_path(table.table_schema)
            tmp_store._write_table(table, path)
            tmp_store.copy_to(self)

    def get_table_path(self, schema: type[IbisSchema]) -> Path:
        """The directory path for a specific `IbisSchema`."""
        return self.local_path / naming.snake_case(schema.__name__)

    @contextmanager
    def tmp_store(self) -> Iterator[Self]:
        """Create a Table Store copy in a temporary directory."""
        with tempfile.TemporaryDirectory() as tmp_path:
            yield attrs.evolve(self, local_path=Path(tmp_path))

    def copy_to(self, other: Self) -> None:
        """Copy all table files from this Store to another."""
        shutil.copytree(self.local_path, other.local_path, dirs_exist_ok=True)

    def log_store_info(self) -> None:
        """Log size information for the Parquet Table Store."""
        root = self.local_path
        paths = (p for p in root.rglob(f"*.{self._file_suffix}") if p.is_file())
        schema_paths = utils.group_by(paths, key=lambda p: p.relative_to(root).parts[0])
        schema_sizes = {
            schema: [path.stat().st_size for path in paths]
            for schema, paths in schema_paths.items()
        }
        tot_sizes = list(itertools.chain(*schema_sizes.values()))

        logger.info(f"Store  {size_stats(tot_sizes)} - {root.name} @ {root.parent}")
        for schema, sizes in schema_sizes.items():
            logger.info(f"Schema {size_stats(sizes)} - {schema}")


@frozen
class ParquetTableStore(LocalTableStore):
    """Store for `IbisTable`s stored in `.parquet` format.

    The `suffix` property controls the exact file extension of table files.
    This can be used for partitioning schemes encoded in the file name.

    The `profile` attribute toggles if expressions should be profiled
    and result in additional `.profiling.json` sibling files.
    """

    connection: IbisConnection = attrs.field(factory=IbisConnection)

    suffix: str = ""
    profile: bool = False

    @contextmanager
    def _with_profiling(self, path: Path):
        # DuckDB Specific.
        # https://duckdb.org/docs/stable/dev/profiling
        con = self.connection.connection
        assert isinstance(con, ibis.backends.duckdb.Backend)
        con.raw_sql(f"""
            PRAGMA enable_profiling = 'json';
            PRAGMA profiling_mode = 'detailed';
            SET profiling_output='{path}';
            """).fetchall()

        yield

        con.raw_sql("""
            PRAGMA disable_profiling;
            PRAGMA disable_profile;
            """)

    @property
    def _file_suffix(self) -> str:
        return (self.suffix + ".parquet").lstrip(".")

    @property
    def _profiling_file_suffix(self) -> str:
        return (self.suffix + ".profile.json").lstrip(".")

    def _read_table[S: IbisSchema](self, schema: type[S], glob: Path) -> IbisTable[S]:
        table = self.connection.read_parquet(glob, schema)
        return force_cast_table(table)

    def _write_table(self, table: IbisTable, path: Path) -> None:
        # Note: Force DB backend to write as correct types as possible.
        table = force_cast_table(table)
        # Note: DuckDB specific
        kwargs: Any = {
            "FILE_SIZE_BYTES": "64MB",
            "FILE_EXTENSION": self._file_suffix,
        }
        if self.profile:
            with self._with_profiling(path / self._profiling_file_suffix):
                self.connection.write_parquet(table, path, **kwargs)
        else:
            self.connection.write_parquet(table, path, **kwargs)

    def write_table(self, table: IbisTable) -> None:
        super().write_table(table)


def force_cast_table[S: IbisSchema](origin: IbisTable[S]) -> IbisTable[S]:
    """Force columns of an IbisTable to be the declared types via explicit casting.

    When relying on external sources for tables,
    types might be similar but slightly different.
    By explicitly invoking the Cast operation on values,
    Ibis will get exactly the expected column types.
    """
    schema = origin.table_schema
    table = origin.table
    cast_params = {
        col: dt.DataType.from_string(typ) for col, typ in schema.table_schema.items()
    }
    cast_ops = {
        col: operations.Cast(op_cast(table[col]), to=typ).to_expr()
        for col, typ in cast_params.items()
    }
    return schema.of(table.select(cast_ops))


def size_stats(sizes: Sequence[int]) -> str:
    """Format file sizes nicely.

    >>> print(size_stats([111, 222]))
    Size: 333 Bytes Files:   2
    >>> print(size_stats([2**40]))
    Size:    1.1 TB Files:   1
    """
    return f"Size: {humanize.naturalsize(sum(sizes, 0)):>9} Files: {len(sizes):>3}"
