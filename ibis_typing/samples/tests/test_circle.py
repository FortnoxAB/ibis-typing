import math

from ibis_typing.samples.sample_transforms import Circle, CircleParameters
from ibis_typing.utils import ApproxFloat


def test_circle_calculations(evaluate_table):
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
            area=ApproxFloat(c.area),
            circumference=ApproxFloat(c.circumference),
        )
        for c in expected
    ]

    assert actual == expected_approx
