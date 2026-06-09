import math

from attrs import frozen
from ibis import literal

from ibis_typing import Expression, IbisSchema, IbisTable, it, this
from ibis_typing.samples.generated import sample_schemas


@frozen
class CircleParameters(IbisSchema):
    diameter: it.Float32 = None


class Circle(sample_schemas.Circle, Expression):
    @classmethod
    def from_expression(cls, params: IbisTable[CircleParameters]):
        cols = params.cols

        table = params.table @ it.Select(
            expr={
                "area": this[cols.diameter] ** literal(2) * literal(math.pi),
                "circumference": this[cols.diameter] * literal(2) * literal(math.pi),
            }
        )

        return cls.of(table)
