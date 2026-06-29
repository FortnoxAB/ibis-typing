from attrs import frozen
from ibis_typing import IbisSchema
from ibis_typing.ibis_types import *

__all__ = [
    "CalendarWidthSnapshot",
]


@frozen
class CalendarWidthSnapshot(IbisSchema):
    checksum_updated_at: Timestamp = None
    day_span: Int64 = None
    dbt_scd_id: String = None
    dbt_updated_at: Timestamp = None
    dbt_valid_from: Timestamp = None
    dbt_valid_to: Timestamp = None

    table_schema = {
        "checksum_updated_at": "timestamp(6)",
        "day_span": "int64",
        "dbt_scd_id": "string",
        "dbt_updated_at": "timestamp(6)",
        "dbt_valid_from": "timestamp(6)",
        "dbt_valid_to": "timestamp(6)",
    }
