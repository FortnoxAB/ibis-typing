from __future__ import annotations

from collections.abc import Sequence
from typing import override

import pytest
from attrs import frozen

from ibis_typing import (
    BucketedInputsExpression,
    ChecksumBuckets,
    IbisSchema,
    evaluator,
    it,
)
from ibis_typing.checksum_buckets import (
    BucketedInputsParams,
    ChecksumParams,
    IncrementalExpression,
    IncrementalParams,
)
from ibis_typing.fixtures.expressions import EvaluateTable, FetchTable
from ibis_typing.ibis_adapter import IbisTable
from ibis_typing.ibis_time import TimestampNow
from ibis_typing.ibis_utils import Aggregate
from ibis_typing.table_provider import TableProviders, provider_from_rows
from ibis_typing.utils import StrDate


@frozen
class Input(IbisSchema):
    group_id: it.Int64 = None
    value: it.Int64 = None


@frozen
class InputChecksumBuckets(ChecksumBuckets):
    group_id: it.Int64 = None
    checksum_updated_at: it.Timestamp = None
    checksum: it.Int64 = None

    incremental_params = ChecksumParams([Input.cols.group_id], inputs=Input)


@frozen
class MyIncrementalExpression(BucketedInputsExpression):
    group_id: it.Int64 = None
    checksum_updated_at: it.Timestamp = None
    value: it.Int64 = None

    incremental_params = BucketedInputsParams(
        [Input.cols.group_id], buckets=InputChecksumBuckets
    )

    @classmethod
    @override
    def from_expression(cls, inputs: IbisTable[Input]):
        args = cls.incremental_params
        table = inputs.table @ Aggregate(
            by=args.group_by,
            arbitrary=[args.updated_at_col],
            sum=[inputs.cols.value],
        )
        return cls.of(table)


now_t0 = StrDate("2025-01-01")
now_t1 = now_t0.plus(1)
inputs_t0 = [
    Input(group_id=1, value=1),
    Input(group_id=1, value=2),
    Input(group_id=2, value=3),
]
inputs_t1 = [
    *inputs_t0,
    Input(group_id=2, value=123),
]
expected_t0 = [
    MyIncrementalExpression(
        group_id=1, checksum_updated_at=now_t0.datetime, value=1 + 2
    ),
    MyIncrementalExpression(group_id=2, checksum_updated_at=now_t0.datetime, value=3),
]
expected_t1 = [
    MyIncrementalExpression(
        group_id=1, checksum_updated_at=now_t0.datetime, value=1 + 2
    ),
    MyIncrementalExpression(
        group_id=2, checksum_updated_at=now_t1.datetime, value=3 + 123
    ),
]


def as_providers(rows: Sequence[IbisSchema]) -> TableProviders:
    return [provider_from_rows(rows)]


def test_IncrementalExpression_full_lifecycle(fetch_table: FetchTable):
    timestamp_t0 = [TimestampNow(now_t0.datetime)]
    timestamp_t1 = [TimestampNow(now_t1.datetime)]

    checksum_table_t0 = evaluator.evaluate_incremental(
        InputChecksumBuckets,
        input_table_providers=as_providers(inputs_t0 + timestamp_t0),
        prior_table_providers=as_providers([]),
    )
    checksum_t0 = fetch_table(checksum_table_t0)

    table_t0 = evaluator.evaluate_incremental(
        MyIncrementalExpression,
        input_table_providers=as_providers(checksum_t0 + inputs_t0 + timestamp_t0),
        prior_table_providers=as_providers([]),
    )

    actual_t0 = fetch_table(table_t0)
    assert actual_t0 == expected_t0

    checksum_table_t1 = evaluator.evaluate_incremental(
        InputChecksumBuckets,
        input_table_providers=as_providers(inputs_t1 + timestamp_t1),
        prior_table_providers=as_providers(checksum_t0),
    )
    checksum_t1 = fetch_table(checksum_table_t1)

    table_t1 = evaluator.evaluate_incremental(
        MyIncrementalExpression,
        input_table_providers=as_providers(checksum_t1 + inputs_t1 + timestamp_t1),
        prior_table_providers=as_providers(actual_t0 + checksum_t0),
    )

    actual_t1 = fetch_table(table_t1)
    assert actual_t1 == expected_t1


def test_check_increment_throws_on_duplicated_key_rows():
    rows = [MyIncrementalExpression() for _ in range(3)]

    evaluator.check_increment(MyIncrementalExpression.of_rows(rows[:1]))
    with pytest.raises(ValueError):
        evaluator.check_increment(MyIncrementalExpression.of_rows(rows[:2]))


def test_evaluate_table_raises_for_duplicated_key_rows_in_incremental_expression(
    evaluate_table: EvaluateTable,
):
    @frozen
    class MyIncrementalModel(IncrementalExpression):
        value: it.Int64 = None

        incremental_params = IncrementalParams(())
        _get_table_schema = IbisSchema._get_table_schema  # pyrefly: ignore[missing-override-decorator]

        @classmethod
        @override
        def from_expression(cls):
            return cls.of_rows(rows)

    cls = MyIncrementalModel

    rows = [cls(1)]
    evaluate_table(MyIncrementalModel, [])

    rows = [cls(1), cls(2)]
    with pytest.raises(ValueError):
        evaluate_table(MyIncrementalModel, [])
