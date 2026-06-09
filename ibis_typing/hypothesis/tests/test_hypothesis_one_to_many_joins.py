"""Sample Hypothesis-based tests of one-to-many join Ibis transforms."""

from typing import NamedTuple

from attrs import frozen
from hypothesis import given
from hypothesis import strategies as st
from ibis import literal

from ibis_typing import Expression, IbisSchema, IbisTable, it, this
from ibis_typing.hypothesis import strategy_for, unique


# Declare input Ibis schemas.
@frozen
class OpeningBalance(IbisSchema):
    tenant_id: it.Int64 = None
    balance: it.Float64 = None


@frozen
class Transaction(IbisSchema):
    tenant_id: it.Int64 = None
    amount: it.Float64 = None


# Declare Ibis expression unit-under-test.
@frozen
class Balance(Expression):
    tenant_id: it.Int64 = None
    balance: it.Float64 = None

    @classmethod
    def from_expression(
        cls,
        opening_balance: IbisTable[OpeningBalance],
        transactions: IbisTable[Transaction],
    ):
        cols = transactions.cols

        transactions_table = transactions.table @ it.Aggregate(
            by=[cols.tenant_id], sum=[cols.amount]
        )
        table = (
            opening_balance.table
            @ it.LeftJoin(transactions_table, keys=[cols.tenant_id])
            @ it.Select(
                cols.tenant_id,
                expr={
                    OpeningBalance.cols.balance: this[OpeningBalance.cols.balance]
                    + this[cols.amount].fill_null(literal(0))
                },
            )
        )

        return cls.of(table)


# Declare test input structure.
class BalanceInputs(NamedTuple):
    opening_balance: OpeningBalance
    transactions: list[Transaction]


# Declare Hypothesis sample strategies.
@st.composite
def tenant_ids(draw: st.DrawFn) -> int:
    return draw(unique(st.integers(min_value=0, max_value=2**30)))


@st.composite
def balance_inputs(draw: st.DrawFn) -> BalanceInputs:
    keys = {OpeningBalance.cols.tenant_id: draw(tenant_ids())}

    balances = strategy_for(OpeningBalance, kwargs=keys)
    transactions = st.lists(
        strategy_for(Transaction, kwargs=keys),
        min_size=0,
        max_size=4,
    )

    return BalanceInputs(draw(balances), draw(transactions))


# Test Ibis expression unit-under-test given random Hypothesis-provided samples.
@given(st.lists(balance_inputs(), min_size=1))
def test_accumulated_balance_per_tenant(evaluate_table, inputs: list[BalanceInputs]):
    def iter_rows():
        # DuckDB requires at least one row for each table.
        yield Transaction()

        for opening_balance, transactions in inputs:
            yield opening_balance
            yield from transactions
            # Calculate expected output in simple Python reference implementation.
            accumulated = sum(transaction.amount or 0 for transaction in transactions)
            yield Balance(
                tenant_id=opening_balance.tenant_id,
                balance=accumulated + (opening_balance.balance or 0),
            )

    actual, expected = evaluate_table(Balance, iter_rows())

    assert actual == expected
