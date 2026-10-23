from __future__ import annotations

from collections.abc import Callable

from attrs import frozen

from ibis_typing import IbisSchema, it
from ibis_typing.checksum_buckets import (
    ChecksumBuckets,
    ChecksumParams,
)
from ibis_typing.fixtures.expressions import EvaluateTable
from ibis_typing.utils import StrDate


@frozen
class Input(IbisSchema):
    group_id: it.Int64 = None
    data: it.Int64 = None


@frozen
class InputChecksumBuckets(ChecksumBuckets):
    group_id: it.Int64 = None
    checksum_updated_at: it.Timestamp = None
    checksum: it.Int64 = None

    incremental_params = ChecksumParams((Input.cols.group_id,), inputs=Input)


def test_ChecksumBuckets_hashes_inputs_into_groups(
    fix_ibis_time: Callable[[StrDate], None],
    ibis_dialect: str,
    evaluate_table: EvaluateTable,
):
    now = StrDate("2021-01-01")
    fix_ibis_time(now)
    is_trino = ibis_dialect == "trino"

    inputs = [
        Input(group_id=1, data=1),
        Input(group_id=1, data=2),
        Input(group_id=2, data=3),
    ]
    hashes = [
        InputChecksumBuckets(
            group_id=1,
            checksum=(7171930684550795574 if is_trino else 6764638988363571842),
            checksum_updated_at=now.datetime,
        ),
        InputChecksumBuckets(
            group_id=2,
            checksum=(5144315941037746383 if is_trino else 8131803788478518982),
            checksum_updated_at=now.datetime,
        ),
    ]

    actual, expected = evaluate_table(InputChecksumBuckets, [*inputs, *hashes])

    assert actual == expected
