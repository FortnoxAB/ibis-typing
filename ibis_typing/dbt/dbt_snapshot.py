"""Integrates DBT Snapshot models via ibis Expression classes."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import ClassVar

from attrs import frozen

from ibis_typing import IbisSchema, IbisTable, it
from ibis_typing.expression import (
    GenericExpression,
    SingleInputTableExpression,
)
from ibis_typing.table_provider import EmptyTableProvider

from .dbt_model import DbtModel, GeneralConfig, PlainStrEnum


@frozen(kw_only=True)
class DbtSnapshot[E: IbisSchema](DbtModel):
    """Integration mark-up for DBT snapshot function."""

    expr: type[E]
    config: SnapshotConfig


class DbtSnapshotAbstract(GenericExpression):
    """Abstract implementation for schema generation."""

    origin: ClassVar[type[IbisSchema]]
    config: ClassVar[SnapshotConfig]

    @classmethod
    def get_table_expression(cls):
        return DbtSnapshotAbstractTableExpression(cls.origin, cls.config)


@frozen(kw_only=True)
class SnapshotConfig(GeneralConfig):
    """DBT Snapshot configuration. Similar to DBT Model.

    See
    https://docs.getdbt.com/reference/snapshot-configs?version=2.0&name=Fusion#snapshot-specific-configurations
    https://docs.getdbt.com/docs/build/snapshots?version=2.0&name=Fusion#configuring-snapshots
    """

    unique_key: Sequence[it.NameOrType]
    strategy: SnapshotStrategy

    updated_at: it.NameOrType | None = None
    check_cols: Sequence[it.NameOrType] | None = None

    snapshot_meta_column_names: Mapping[it.NameOrType, it.NameOrType] | None = None
    hard_deletes: HardDeletes | None = None
    dbt_valid_to_current: str | None = None

    def __attrs_post_init__(self):
        match self.strategy:
            case SnapshotStrategy.check:
                assert self.check_cols is not None
            case SnapshotStrategy.timestamp:
                assert self.updated_at is not None


class SnapshotStrategy(PlainStrEnum):
    timestamp = "timestamp"
    check = "check"


class HardDeletes(PlainStrEnum):
    ignore = "ignore"
    invalidate = "invalidate"
    new_record = "new_record"


@frozen
class DbtSnapshotAbstractTableExpression(SingleInputTableExpression):
    config: SnapshotConfig

    @property
    def input_schemas(self):
        return {"origin": self.origin}

    def __call__(self, origin: IbisTable):
        defaults = EmptyTableProvider()(SnapshotsCols).table
        delete_cols = (
            EmptyTableProvider()(SnapshotHardDeleteNewRecordCols).table
            if self.config.hard_deletes == HardDeletes.new_record
            else ()
        )
        col_names = self.config.snapshot_meta_column_names or {}
        renames = {new: old for old, new in col_names.items()}
        return (
            origin.table
            @ it.InnerJoin(defaults, *delete_cols, keys=())
            @ it.deferred.rename(renames)
        )


@frozen
class SnapshotsCols(IbisSchema):
    """DBT snapshot model markup.

    See:
    https://docs.getdbt.com/reference/resource-configs/snapshot_meta_column_names?version=2.0&name=Fusion#default
    """

    dbt_scd_id: it.String = None
    dbt_updated_at: it.Timestamp = None
    dbt_valid_from: it.Timestamp = None
    dbt_valid_to: it.Timestamp = None

    table_schema: ClassVar[Mapping[str, str]] = {
        "dbt_scd_id": "string",
        "dbt_updated_at": "timestamp(6)",
        "dbt_valid_from": "timestamp(6)",
        "dbt_valid_to": "timestamp(6)",
    }


@frozen
class SnapshotHardDeleteNewRecordCols(IbisSchema):
    dbt_is_deleted: it.Boolean = None
