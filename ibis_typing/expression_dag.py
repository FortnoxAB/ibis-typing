"""Resolve the dependency DAG between Expressions using only the standard library."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from graphlib import TopologicalSorter

from ibis_typing import Expression, IbisSchema

type ExpressionInputs = dict[type[Expression], list[type[IbisSchema]]]


def get_expression_dag(expressions: Iterable[type[Expression]]) -> ExpressionInputs:
    """Map the DAG structure of the given Expressions in topological order.

    >>> from ibis_typing.samples import sample_transforms
    >>> get_expression_dag([sample_transforms.Circle])
    {<class 'ibis_typing.samples.sample_transforms.Circle'>: [<class 'ibis_typing.samples.sample_transforms.CircleParameters'>]}
    """
    schema_input_map: ExpressionInputs = {}
    _add_all_dependencies(expressions, schema_input_map)
    sorter: TopologicalSorter[type[IbisSchema]] = TopologicalSorter(schema_input_map)
    return {
        expr: schema_input_map[expr]
        for expr in sorter.static_order()
        if issubclass(expr, Expression)
    }


def _add_all_dependencies(
    schemas: Iterable[type[IbisSchema]], schema_input_map: ExpressionInputs
) -> None:
    for schema in schemas:
        _add_dependencies(schema, schema_input_map)


def _add_dependencies(
    schema: type[IbisSchema], schema_input_map: ExpressionInputs
) -> None:
    if not issubclass(schema, Expression) or schema in schema_input_map:
        return

    inputs = [*schema.get_parameter_schema_types().values()]
    schema_input_map[schema] = inputs

    _add_all_dependencies(inputs, schema_input_map)


def filter_dag_on_column(
    start_node: type[Expression], dag: ExpressionInputs, column: str
) -> ExpressionInputs:
    found: ExpressionInputs = defaultdict(list)

    def recurse(search_next: type[Expression]) -> None:
        for node in dag[search_next]:
            schema = getattr(node, "table_schema", None)
            if schema and column in schema:
                found[search_next].append(node)
                # Only Expressions have inputs to search.
                if issubclass(node, Expression):
                    recurse(node)

    recurse(start_node)
    return found
