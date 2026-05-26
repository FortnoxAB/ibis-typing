from attrs import frozen

from ibis_typing import IbisSchema, it
from ibis_typing.ibis_joins import AntiJoin, LeftJoin
from tests.conftest import SimpleSchema


def test_left_join_without_duplicates(fetch_table):
    @frozen
    class RightSchema(IbisSchema):
        id: it.Int64
        other: it.Int64

    @frozen
    class JoinedSchema(SimpleSchema):
        other: it.Int64

    left = [
        SimpleSchema(id=0, value=1),
        SimpleSchema(id=2, value=3),
    ]
    right = [
        RightSchema(id=0, other=2),
        RightSchema(id=1, other=4),
    ]
    expected = [
        JoinedSchema(id=0, value=1, other=2),
        JoinedSchema(id=2, value=3, other=None),
    ]

    table = SimpleSchema.of_rows(left).table @ LeftJoin(
        RightSchema.of_rows(right).table,
        keys=[SimpleSchema.cols.id],
    )
    actual = fetch_table(JoinedSchema.of(table))

    assert actual == expected


def test_anti_join_excludes_matching_rows(fetch_table):
    @frozen
    class RightSchema(IbisSchema):
        id: it.Int64

    left = [
        SimpleSchema(id=0, value=1),
        SimpleSchema(id=1, value=2),
        SimpleSchema(id=2, value=3),
    ]
    right = [
        RightSchema(id=0),
        RightSchema(id=2),
    ]
    expected = [
        SimpleSchema(id=1, value=2),
    ]

    table = SimpleSchema.of_rows(left).table @ AntiJoin(
        RightSchema.of_rows(right).table,
        keys=[SimpleSchema.cols.id],
    )
    actual = fetch_table(SimpleSchema.of(table))

    assert actual == expected
