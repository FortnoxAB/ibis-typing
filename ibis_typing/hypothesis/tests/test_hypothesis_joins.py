"""Samples of Hypothesis-based testing of Ibis expressions with joins."""

from __future__ import annotations

import itertools
import operator
import uuid
from typing import NamedTuple

from attrs import frozen
from hypothesis import given
from hypothesis import strategies as st

from ibis_typing import Expression, IbisSchema, IbisTable, it
from ibis_typing.hypothesis import strategy_for
from ibis_typing.ibis_joins import LeftJoin, OuterJoin
from ibis_typing.reference import py_join


# Declare input schemas for Ibis expression unit-under-test.
@frozen
class Client(IbisSchema):
    client_id: it.UUID = None
    factoring_license: it.Boolean = None

    has_manual_review: it.Boolean = None
    updated_at: it.Date = None
    risk_level: it.Int64 = None


@frozen
class Tenant(IbisSchema):
    tenant_id: it.Int64 = None
    bookkeeping_license: it.Boolean = None

    has_manual_review: it.Boolean = None
    updated_at: it.Date = None
    risk_level: it.Int64 = None


@frozen
class ClientTenantMapping(IbisSchema):
    client_id: it.UUID = None
    tenant_id: it.Int64 = None


# Declare Ibis expression unit-under-test with a python reference implementation.
@frozen
class CompositeClientTenant(Expression):
    client_id: it.UUID = None
    factoring_license: it.Boolean = None

    has_manual_review: it.Boolean = None
    updated_at: it.Date = None
    risk_level: it.Int64 = None

    tenant_id: it.Int64 = None
    bookkeeping_license: it.Boolean = None

    @classmethod
    def from_expression(
        cls,
        client: IbisTable[Client],
        tenant: IbisTable[Tenant],
        mapping: IbisTable[ClientTenantMapping],
    ):
        table = (
            client.table
            @ LeftJoin(
                mapping.table,
                keys=[mapping.cols.client_id],
            )
            @ LeftJoin(
                tenant.table,
                keys=[mapping.cols.tenant_id],
                arbitrary=[client.cols.has_manual_review],
                max=[client.cols.updated_at],
                min=[client.cols.risk_level],
            )
        )
        return cls.of(table)

    @classmethod
    def from_py(
        cls,
        client: list[Client],
        tenant: list[Tenant],
        mapping: list[ClientTenantMapping],
    ):
        cols = cls.cols
        table = py_join.left_join(
            client,
            mapping,
            keys=[cols.client_id],
        )
        table = py_join.left_join(
            table,
            tenant,
            keys=[cols.tenant_id],
            arbitrary=[cols.has_manual_review],
            max=[cols.updated_at],
            min=[cols.risk_level],
        )
        return py_join.to_schema(table, cls)


# Declare test input structure.
class Inputs(NamedTuple):
    mapping: ClientTenantMapping
    client: Client
    tenant: Tenant


@st.composite
def inputs_strategy(draw: st.DrawFn) -> Inputs:
    mappings = strategy_for(
        (t := ClientTenantMapping), uniques=[t.cols.tenant_id, t.cols.client_id]
    )
    mapping = draw(mappings)
    clients = strategy_for((t := Client), kwargs={t.cols.client_id: mapping.client_id})
    tenants = strategy_for((t := Tenant), kwargs={t.cols.tenant_id: mapping.tenant_id})
    return Inputs(mapping, draw(clients), draw(tenants))


# Test the Ibis expression given random samples
@given(st.lists(inputs_strategy(), min_size=1))
def test_join_client_tenant_composite(evaluate_table, inputs: list[Inputs]):
    # Describe expected outputs given generated input samples.
    outputs = [
        CompositeClientTenant(
            client_id=client.client_id,
            factoring_license=client.factoring_license,
            tenant_id=tenant.tenant_id,
            bookkeeping_license=tenant.bookkeeping_license,
            # Column duplication elimination strategies
            has_manual_review=c
            if (c := client.has_manual_review) is not None
            else tenant.has_manual_review,
            updated_at=max(c, tenant.updated_at or c)
            if (c := client.updated_at) is not None
            else tenant.updated_at,
            risk_level=min(c, tenant.risk_level or c)
            if (c := client.risk_level) is not None
            else tenant.risk_level,
        )
        for mapping, client, tenant in inputs
    ]

    rows = [row for rows in inputs for row in rows] + outputs
    actual, expected = evaluate_table(CompositeClientTenant, rows)

    assert actual == expected


@given(inputs=st.lists(inputs_strategy(), min_size=1))
def test_ibis_join_against_python_implementation(evaluate_table, inputs: list[Inputs]):
    mapping, client, tenant = (
        [operator.itemgetter(i)(triple) for triple in inputs] for i in range(3)
    )
    outputs = CompositeClientTenant.from_py(client, tenant, mapping)
    rows = [*itertools.chain(*inputs), *outputs]
    actual, expected = evaluate_table(CompositeClientTenant, rows)

    assert actual == expected


# Test using explicit input and output examples without reference implementation.
def test_join_client_tenant_composite_without_hypothesis(evaluate_table):
    # Declare input samples.
    clients = [
        Client(client_id=uuid.UUID(int=1), factoring_license=True),
        Client(client_id=uuid.UUID(int=2), factoring_license=False),
    ]
    tenants = [
        Tenant(tenant_id=1, bookkeeping_license=True),
        Tenant(tenant_id=2, bookkeeping_license=False),
    ]
    mappings = [
        ClientTenantMapping(client_id=client.client_id, tenant_id=tenant.tenant_id)
        for client, tenant in zip(clients, tenants)
    ]

    # Describe expected outputs.
    outputs = [
        CompositeClientTenant(
            client_id=client.client_id,
            factoring_license=client.factoring_license,
            tenant_id=tenant.tenant_id,
            bookkeeping_license=tenant.bookkeeping_license,
        )
        for client, tenant in zip(clients, tenants)
    ]

    rows = [*clients, *tenants, *mappings, *outputs]
    actual, expected = evaluate_table(CompositeClientTenant, rows)

    assert actual == expected


@frozen
class OuterJoinTransform(ClientTenantMapping, Expression):
    @classmethod
    def from_expression(
        cls, tenants: IbisTable[Tenant], mappings: IbisTable[ClientTenantMapping]
    ):
        table = (
            tenants.table
            @ OuterJoin(
                mappings.table,
                keys=[mappings.cols.tenant_id],
            )
            @ it.deferred.select(*mappings.table.columns)
        )
        return cls.of(table)

    @classmethod
    def from_py(
        cls, tenants: list[Tenant], mappings: list[ClientTenantMapping]
    ) -> list[ClientTenantMapping]:
        table = py_join.outer_join(
            tenants,
            mappings,
            keys=[Tenant.cols.tenant_id],
        )
        table = py_join.select(table, *ClientTenantMapping.table_schema)
        return py_join.to_schema(table, cls)


@given(
    tenants=st.lists(strategy_for(Tenant, uniques=[Tenant.cols.tenant_id]), min_size=1),
    mappings=st.lists(
        strategy_for(ClientTenantMapping, uniques=[Tenant.cols.tenant_id]), min_size=1
    ),
)
def test_outer_join(
    evaluate_table, tenants: list[Tenant], mappings: list[ClientTenantMapping]
):
    outputs = OuterJoinTransform.from_py(tenants, mappings)
    rows = [*tenants, *mappings, *outputs]
    actual, expected = evaluate_table(OuterJoinTransform, rows)

    assert actual == expected
