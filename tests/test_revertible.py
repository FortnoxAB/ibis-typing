import uuid
from typing import ClassVar

from attrs import frozen

from ibis_typing import IbisSchema, evaluator, it, revertible
from ibis_typing.revertible import AsRevertible, ExpressionExport, UUIDToStringExport


def test_uuid_to_string_export_lifecycle(fetch_table):
    @frozen
    class BaseSchema(IbisSchema):
        val: it.UUID = None

        table_schema: ClassVar = {"val": "uuid"}

    hive_export = (
        BaseSchema @ AsRevertible(ExpressionExport) @ AsRevertible(UUIDToStringExport)
    )

    data = [BaseSchema(val=uuid.UUID(int=1))]

    inputs = BaseSchema.of_rows(data)
    exported = evaluator.from_expression(hive_export, inputs)
    assert exported.table_schema.table_schema["val"] == "string"
    imported = revertible.revert_all(exported)

    actual = fetch_table(imported)

    assert actual == data
