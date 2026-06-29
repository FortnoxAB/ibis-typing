"""Automatic discovery of DBT Model candidates."""

from types import ModuleType

from attrs import frozen

from ibis_typing import (
    ChecksumBuckets,
    Expression,
    IbisSchema,
    IncrementalExpression,
    schema_writer,
)

from .dbt_snapshot import DbtSnapshotAbstract


@frozen
class DbtModelResolver:
    package: ModuleType

    @property
    def expressions(self) -> set[type[Expression]]:
        return set(schema_writer.list_expressions_in_package(self.package))

    @property
    def snapshots(self) -> set[type[DbtSnapshotAbstract]]:
        return {
            expr for expr in self.expressions if issubclass(expr, DbtSnapshotAbstract)
        }

    @property
    def incremental_models(self) -> set[type[IncrementalExpression]]:
        return {
            expr for expr in self.expressions if issubclass(expr, IncrementalExpression)
        }

    @property
    def checksums(self) -> set[type[ChecksumBuckets]]:
        return {expr for expr in self.expressions if issubclass(expr, ChecksumBuckets)}

    @property
    def checksum_inputs(self) -> set[type[IbisSchema]]:
        return {checksum.incremental_params.inputs for checksum in self.checksums}
