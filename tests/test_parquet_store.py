import json
from pathlib import Path
from unittest import mock

from attrs import frozen

from ibis_typing import IbisSchema, it, naming
from ibis_typing.ibis_pyarrow import EvaluateIbisTable
from ibis_typing.table_store import ParquetTableStore


@frozen
class InputSchema(IbisSchema):
    id: it.Int64
    name: it.String


class OutputSchema(IbisSchema):
    pass


def test_parquet_table_store_roundtrip(tmp_path: Path):
    store = ParquetTableStore(tmp_path)

    expected = [InputSchema(id=1, name="test")]
    table = InputSchema.of_rows(expected)

    assert InputSchema not in store

    bucket_dir_name = "tenant_id_bucket=5"
    with store.tmp_store() as tmp_store:
        tmp_store.write_table(table)
        nested = store.get_table_path(InputSchema) / bucket_dir_name
        nested.mkdir(parents=True)
        for path in tmp_store.get_table_path(InputSchema).rglob("*.parquet"):
            (nested / path.name).write_bytes(path.read_bytes())
            path.unlink()

    assert InputSchema in store
    files = [
        path.relative_to(store.local_path)
        for path in store.local_path.rglob("*.parquet")
        if path.is_file()
    ]
    expected_files = [
        Path(naming.snake_case(InputSchema.__name__))
        / bucket_dir_name
        / "data_0.parquet"
    ]
    assert files == expected_files

    restored = store(InputSchema)
    assert restored
    actual = list(restored @ EvaluateIbisTable())

    assert actual == expected


def test_parquet_table_store_profiling(tmp_path: Path):
    store = ParquetTableStore(tmp_path, profile=True)

    expected = [InputSchema(id=1, name="test")]
    table = InputSchema.of_rows(expected)

    assert InputSchema not in store
    store.write_table(table)
    assert InputSchema in store
    files = [
        path.relative_to(store.local_path)
        for path in store.local_path.rglob("*.json")
        if path.is_file()
    ]
    expected_profile = Path(naming.snake_case(InputSchema.__name__)) / "profile.json"
    expected_files = [expected_profile]
    assert files == expected_files
    actual_file = store.local_path / expected_profile
    profile = json.loads(actual_file.read_text())
    assert profile.get("latency") != 0.0


def test_parquet_table_store_can_create_tmp_store(tmp_path):
    store = ParquetTableStore(tmp_path)
    expected = ParquetTableStore(
        mock.ANY,
        store.connection,
        suffix=store.suffix,
        profile=store.profile,
    )

    with store.tmp_store() as tmp_store:
        assert tmp_store == expected
        assert tmp_store.local_path != store.local_path

    assert not tmp_store.local_path.exists()
