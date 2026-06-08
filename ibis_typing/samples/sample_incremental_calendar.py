from attrs import frozen

from ibis_typing import it, this
from ibis_typing.checksum_buckets import (
    BucketedInputsExpression,
    BucketedInputsParams,
    ChecksumBuckets,
    ChecksumParams,
)
from ibis_typing.ibis_adapter import IbisSchema, IbisTable
from ibis_typing.ibis_time import DaysSince
from ibis_typing.ibis_utils import Aggregate
from ibis_typing.samples.generated import sample_schemas


@frozen
class Calendar(IbisSchema):
    day: it.Date = None


class CalendarChecksumBucket(sample_schemas.CalendarChecksumBucket, ChecksumBuckets):
    incremental_params = ChecksumParams((), inputs=Calendar)


class CalendarWidth(sample_schemas.CalendarWidth, BucketedInputsExpression):
    incremental_params = BucketedInputsParams(
        group_by=(), buckets=CalendarChecksumBucket
    )

    @classmethod
    def from_expression(cls, inputs: IbisTable[Calendar]):
        cols = inputs.cols

        args = cls.incremental_params
        table = inputs.table @ Aggregate(
            by=args.group_by,
            arbitrary=[args.updated_at_col],
            expr={
                "day_span": this[cols.day].max() @ DaysSince(this[cols.day].min()),
            },
        )

        return cls.of(table)
