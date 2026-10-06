from __future__ import annotations

import math
from typing import Any

import ibis
import pytest

from ibis_typing.time_series.features import Sum
from tests.time_series.series import extraction, table


@pytest.mark.parametrize(
    ("overrides", "error", "message"),
    [
        ({"columns": ()}, ValueError, "at least one column"),
        ({"windows": ()}, ValueError, "at least one window"),
        ({"windows": (3, 0)}, ValueError, "at least 1"),
        ({"windows": True}, TypeError, "must be ints"),
        ({"windows": (3, 2.0)}, TypeError, "must be ints"),
        ({"sampling_frequency": 0.0}, ValueError, "positive and finite"),
        ({"sampling_frequency": math.nan}, ValueError, "positive and finite"),
        ({"sampling_frequency": math.inf}, ValueError, "positive and finite"),
        ({"columns": ("missing",)}, ValueError, "not in table"),
        ({"order_by": "missing"}, ValueError, "not in table"),
        ({"keys": ("missing",)}, ValueError, "not in table"),
        ({"keys": ("key", "value")}, ValueError, "both a key and a value column"),
        ({"keys": ("key", "time")}, ValueError, "order_by cannot also be a key"),
        ({"columns": ("key",)}, ValueError, "must be numeric"),
    ],
)
def test_invalid_arguments_are_rejected(overrides, error, message):
    method = extraction(Sum(), **overrides)
    with pytest.raises(error, match=message):
        _ = table() @ method


def test_at_least_one_feature_is_required():
    with pytest.raises(ValueError, match="at least one feature"):
        _ = table() @ extraction()


def test_features_must_be_point_or_spectral_features():
    not_a_feature: Any = "sum"
    with pytest.raises(TypeError, match="PointFeature or SpectralFeature"):
        _ = table() @ extraction(not_a_feature)


def test_the_same_output_column_cannot_be_produced_twice():
    with pytest.raises(ValueError, match="Duplicate output"):
        _ = table() @ extraction(Sum(), Sum())


def test_input_columns_cannot_use_the_reserved_helper_prefix():
    reserved = table().mutate(__ts_position=ibis.literal(0))
    with pytest.raises(ValueError, match="reserved prefix '__ts_'"):
        _ = reserved @ extraction(Sum())


def test_existing_columns_are_never_overwritten():
    existing = table().mutate(value__sum_last_2=ibis.literal(0.0))
    with pytest.raises(ValueError, match="already exist"):
        _ = existing @ extraction(Sum())
