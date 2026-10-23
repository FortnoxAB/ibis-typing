import math
from typing import cast

from ibis_typing.fixtures.expressions import EvaluateTable
from ibis_typing.samples.sample_transforms import Circle, CircleParameters
from ibis_typing.utils import ApproxFloat


def test_circle_calculations(evaluate_table: EvaluateTable):
    inputs = [
        CircleParameters(diameter=10.0),
    ]
    outputs = [
        Circle(
            diameter=(d := p.diameter),
            area=d and d**2 * math.pi,
            circumference=d and d * 2 * math.pi,
        )
        for p in inputs
    ]
    rows = inputs + outputs
    actual, expected = evaluate_table(Circle, rows)

    expected_approx = [
        Circle(
            diameter=c.diameter,
            # Fetched rows hold plain Python values.
            area=ApproxFloat(cast(float, c.area)),
            circumference=ApproxFloat(cast(float, c.circumference)),
        )
        for c in expected
    ]

    assert actual == expected_approx
