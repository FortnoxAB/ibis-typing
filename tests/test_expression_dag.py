from typing import override

from attrs import frozen

from ibis_typing import Expression, IbisSchema, IbisTable, it
from ibis_typing.expression_dag import filter_dag_on_column, get_expression_dag


@frozen
class Source(IbisSchema):
    key: it.String = None
    amount: it.Int64 = None


@frozen
class Other(IbisSchema):
    other_id: it.String = None


@frozen
class Middle(Expression):
    key: it.String = None
    amount: it.Int64 = None

    @classmethod
    @override
    def from_expression(cls, source: IbisTable[Source]):
        return cls.of(source.table)


@frozen
class Top(Expression):
    key: it.String = None
    other_id: it.String = None

    @classmethod
    @override
    def from_expression(
        cls, middle: IbisTable[Middle], other: IbisTable[Other]
    ) -> IbisTable["Top"]:
        raise NotImplementedError  # Never evaluated: only its inputs' schemas are read.


@frozen
class Leaf(Expression):
    key: it.String = None

    @classmethod
    @override
    def from_expression(cls) -> IbisTable["Leaf"]:
        raise NotImplementedError  # Never evaluated: only its signature is read.


def test_get_expression_dag_orders_inputs_before_dependents():
    dag = get_expression_dag([Top])

    assert list(dag) == [Middle, Top]
    assert dag == {Middle: [Source], Top: [Middle, Other]}


def test_get_expression_dag_excludes_plain_schemas_from_keys():
    dag = get_expression_dag([Top])

    assert Source not in dag
    assert Other not in dag


def test_get_expression_dag_keeps_expressions_without_inputs():
    assert get_expression_dag([Leaf]) == {Leaf: []}


def test_get_expression_dag_resolves_shared_inputs_once():
    assert get_expression_dag([Top, Middle]) == get_expression_dag([Top])


def test_filter_dag_on_column_keeps_ancestors_carrying_the_column():
    dag = get_expression_dag([Top])

    assert filter_dag_on_column(Top, dag, "key") == {Top: [Middle], Middle: [Source]}


def test_filter_dag_on_column_stops_at_inputs_without_the_column():
    dag = get_expression_dag([Top])

    assert filter_dag_on_column(Top, dag, "other_id") == {Top: [Other]}


def test_filter_dag_on_column_is_empty_for_unknown_column():
    dag = get_expression_dag([Top])

    assert filter_dag_on_column(Top, dag, "missing") == {}
