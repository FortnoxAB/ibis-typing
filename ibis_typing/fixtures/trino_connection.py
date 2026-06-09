"""Container-based Trino server fixture."""

import os
import time

import pytest
from ibis import literal
from ibis.backends import trino
from testcontainers.core.container import DockerContainer

from ibis_typing import IbisConnection

TRINO_IMAGE = "trinodb/trino:474"
TRINO_PORT = 8080


@pytest.fixture(scope="session")
def trino_connection(trino_session_container) -> IbisConnection:
    host, port = get_container_host_port(trino_session_container, TRINO_PORT)

    (con := trino.Backend()).do_connect(
        host=host,
        port=port,
        database="memory",
        schema="default",
    )
    connection = IbisConnection(con)
    wait_for_ibis_connection(connection, timeout_s=60)
    return connection


@pytest.fixture(scope="session")
def trino_session_container(
    container_name: str | None = None, port: int | None = None
) -> DockerContainer:
    container_name = container_name or f"trino-{time.time()}"
    command = """
    sh -c "echo '
        catalog.management=dynamic
        ' > etc/trino/config.properties && /usr/lib/trino/bin/run-trino"
    """
    return (
        DockerContainer(TRINO_IMAGE)
        .with_name(container_name)
        .with_bind_ports(TRINO_PORT, port)
        .with_command(command)
        .start()
    )


def wait_for_ibis_connection(connection: IbisConnection, timeout_s: float) -> None:
    start = time.time()
    while time.time() - start < timeout_s:
        try:
            connection.evaluate(literal(1))
        except Exception:
            time.sleep(1)
            continue

        return

    raise TimeoutError(f"SQL server did not start in {timeout_s} seconds")


def get_container_host_port(trino_container: DockerContainer, port) -> tuple[str, int]:
    if tc_host := os.environ.get("TESTCONTAINERS_HOST_OVERRIDE"):
        os.environ["TC_HOST"] = tc_host

    host = trino_container.get_container_host_ip()
    # if Windows sets `localnpipe` as host, it will not work, hence revert to localhost
    if host == "localnpipe":
        host = "localhost"

    port = int(trino_container.get_exposed_port(port))
    return host, port
