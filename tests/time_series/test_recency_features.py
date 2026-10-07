from __future__ import annotations

import re
from typing import ClassVar

import ibis
import pytest
from attrs import frozen
from ibis import ir

from ibis_typing.time_series.features import PointFeature, Points
from tests.time_series.series import extraction, table


@frozen
class RecencyWeightedMean(PointFeature):
    """Mean weighted by position: the newest point weighs most."""

    windowable: ClassVar[bool] = False

    def reduce(self, points: Points) -> ir.Value:
        weight = points.position + 1
        return (points.values * weight).sum() / weight.sum()


@frozen
class LatestStep(PointFeature):
    """The newest step: combines `previous_values` and `steps_from_newest`."""

    windowable: ClassVar[bool] = False
    uses_lag: ClassVar[bool] = True

    def reduce(self, points: Points) -> ir.Value:
        step = points.values - points.previous_values
        return step.max(where=points.steps_from_newest == ibis.literal(0))


@frozen
class ReadsPositionWhileWindowable(PointFeature):
    def reduce(self, points: Points) -> ir.Value:
        return points.position.max()


@frozen
class ReadsStepsFromNewestWhileWindowable(PointFeature):
    def reduce(self, points: Points) -> ir.Value:
        return points.steps_from_newest.max()


@frozen
class ReadsPreviousValuesWithoutLag(PointFeature):
    def reduce(self, points: Points) -> ir.Value:
        return points.previous_values.max()


def test_features_can_weight_recent_points_by_position(trailing):
    # (0·1 + 0·2 + 6·3) / (1 + 2 + 3)
    assert trailing([0.0, 0.0, 6.0], RecencyWeightedMean(), window_size=3) == [
        None,
        None,
        3.0,
    ]


def test_features_can_combine_previous_values_and_steps_from_newest(trailing):
    assert trailing([1.0, 4.0, 10.0, 11.0], LatestStep(), window_size=3) == [
        None,
        None,
        6.0,
        1.0,
    ]


def test_positions_require_windowable_false():
    message = re.escape("ReadsPositionWhileWindowable uses Points.position")
    with pytest.raises(TypeError, match=message):
        _ = table() @ extraction(ReadsPositionWhileWindowable())


def test_steps_from_newest_requires_windowable_false():
    message = re.escape(
        "ReadsStepsFromNewestWhileWindowable uses Points.steps_from_newest"
    )
    with pytest.raises(TypeError, match=message):
        _ = table() @ extraction(ReadsStepsFromNewestWhileWindowable())


def test_previous_values_require_uses_lag():
    message = re.escape("ReadsPreviousValuesWithoutLag uses Points.previous_values")
    with pytest.raises(TypeError, match=message):
        _ = table() @ extraction(ReadsPreviousValuesWithoutLag())
