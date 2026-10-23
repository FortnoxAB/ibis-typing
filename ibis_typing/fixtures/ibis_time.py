"""Fixtures for consistent time in tests."""

import os
from collections.abc import Callable

import pytest
from ibis import literal

from ibis_typing import PatchTarget, ibis_time
from ibis_typing.utils import StrDate


@pytest.fixture
def fix_ibis_time(monkeypatch: pytest.MonkeyPatch) -> Callable[[StrDate], None]:
    def set_fix_time(date: StrDate):
        monkeypatch.setattr(
            PatchTarget.of(ibis_time).now,
            lambda: literal(date.datetime).cast("timestamp(6)"),
        )

    return set_fix_time


@pytest.fixture
def today(fix_ibis_time: Callable[[StrDate], None]) -> StrDate:
    today = StrDate("2023-01-15")
    fix_ibis_time(today)
    return today


@pytest.fixture
def update_expected() -> bool:
    return bool(os.getenv("UPDATE_EXPECTED"))
