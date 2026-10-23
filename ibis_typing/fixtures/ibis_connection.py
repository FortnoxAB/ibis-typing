"""
Fixture for running tests against both Trino and DuckDB backend.

Ensure consistency between the two backends by running the same tests against
both for crucial functionality.
"""

from typing import cast

import pytest

from .. import IbisConnection
from . import marks
from .marks import IbisBackends


def _replace_ibis_connection_fixture(_):
    return {
        IbisBackends.duck: duck_ibis_connection,
        IbisBackends.trino: trino_ibis_connection,
        None: any_ibis_connection,
    }[marks.TEST_IBIS_BACKEND]


@pytest.fixture(params=list(IbisBackends))
def any_ibis_connection(
    request: pytest.FixtureRequest,
    trino_connection: IbisConnection,
    duck_connection: IbisConnection,
) -> IbisConnection:
    backend = cast(IbisBackends, request.param)

    skip_if_backend_is_deselected(backend, request)

    return {
        IbisBackends.duck: duck_connection,
        IbisBackends.trino: trino_connection,
    }[backend]


@pytest.fixture
def duck_ibis_connection(
    request: pytest.FixtureRequest, duck_connection: IbisConnection
) -> IbisConnection:
    skip_if_backend_is_deselected(IbisBackends.duck, request)

    return duck_connection


@pytest.fixture
def trino_ibis_connection(
    request: pytest.FixtureRequest,
    trino_connection: IbisConnection,
) -> IbisConnection:
    skip_if_backend_is_deselected(IbisBackends.trino, request)

    return trino_connection


@_replace_ibis_connection_fixture
@pytest.fixture
def ibis_connection() -> IbisConnection:
    raise NotImplementedError


@pytest.fixture
def ibis_dialect(ibis_connection: IbisConnection) -> str:
    return ibis_connection.dialect


def skip_if_backend_is_deselected(
    backend: IbisBackends,
    request: pytest.FixtureRequest,
):
    markers = request.node.own_markers

    selected = get_marks(marks.select_backend_for_test, markers)
    if selected and backend not in selected:
        pytest.skip(f"Backend {backend} not selected.")

    deselected = get_marks(marks.deselect_backend_for_test, markers).get(backend)
    if deselected:
        pytest.skip(f"Backend {backend} deselected. Reason: {deselected.args[1]}")


def get_marks(target_mark: pytest.MarkDecorator, markers: list[pytest.Mark]):
    return {mark.args[0]: mark for mark in markers if mark.name == target_mark.name}
