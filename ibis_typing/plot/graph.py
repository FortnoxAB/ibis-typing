"""Generate a DAG for Expressions."""

from __future__ import annotations

import html
import importlib
from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from typing import Any, Protocol, cast

import graphviz
import networkx as nx
from attrs import frozen
from matplotlib import pyplot as plt
from matplotlib.figure import Figure

from ibis_typing import Expression, IbisSchema


def import_expression_by_name(qualified_name: str) -> type[Expression]:
    """Import Expression classes by qualified name.

    >>> import_expression_by_name("ibis_typing.samples.sample_transforms.Circle")
    <class 'ibis_typing.samples.sample_transforms.Circle'>
    """

    package, expr = qualified_name.rsplit(".", 1)
    module = importlib.import_module(package)
    table = getattr(module, expr)
    assert issubclass(table, Expression)
    return table


type ExpressionInputs = dict[type[Expression], list[type[IbisSchema]]]


def get_expression_dag(expressions: Iterable[type[Expression]]) -> ExpressionInputs:
    """Map the DAG structure of the given Expressions in topological order.

    >>> from ibis_typing.samples import sample_transforms
    >>> get_expression_dag([sample_transforms.Circle])
    {<class 'ibis_typing.samples.sample_transforms.Circle'>: [<class 'ibis_typing.samples.sample_transforms.CircleParameters'>]}
    """
    schema_input_map: ExpressionInputs = {}
    _add_all_dependencies(expressions, schema_input_map)
    dag = nx.DiGraph(
        (source, target)
        for target, sources in schema_input_map.items()
        for source in (sources or [IbisSchema])
        # Keep Expressions without any inputs
    )
    return {
        expr: schema_input_map[expr]
        for expr in nx.topological_sort(dag)
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


def create_graph(data: ExpressionInputs) -> nx.DiGraph[str]:
    dag = nx.DiGraph()
    for target, sources in data.items():
        target_schema = getattr(target, "table_schema", {})
        dag.add_node(target.__name__, schema=target_schema)
        for source in sources:
            source_schema = getattr(source, "table_schema", {})
            common_columns = set(target_schema.keys()).intersection(
                set(source_schema.keys())
            )
            dag.add_edge(
                source.__name__, target.__name__, common_columns=common_columns
            )

    dag.graph["graph"] = {"rankdir": "TD"}
    return dag


class ColorProvider(Protocol):
    def __call__(self, graph: nx.DiGraph[str]) -> Sequence[str]: ...


@frozen
class NodeColors(ColorProvider):
    color_by_name: Mapping[str, str] = {}

    default: str = "lightblue"
    start: str = "lightcoral"
    end: str = "green"

    def __call__(self, graph: nx.DiGraph[str]) -> Sequence[str]:
        return [self.color(node, graph) for node in graph.nodes]

    def color(self, node: Any, graph: nx.DiGraph[str]) -> str:
        if graph.in_degree[node] == 0:
            return self.start
        if graph.out_degree[node] == 0:
            return self.end

        for part, color in self.color_by_name.items():
            if part in node.lower():
                return color

        return self.default


@frozen
class ColumnColorProvider:
    color_map: dict[str, str]

    DEFAULT_EDGE_COLOR: str = "black"
    DEFAULT_CELL_COLOR: str = "white"

    @classmethod
    def with_default_colors(cls, columns: list[str] | None) -> ColumnColorProvider:
        default_palette: list[str] = [
            "#FF5733",  # Red-Orange
            "#33FF57",  # Bright Green
            "#3357FF",  # Blue
            "#FF33A1",  # Pink
            "#A133FF",  # Purple
            "#33FFF6",  # Cyan
            "#F6FF33",  # Yellow
            "#FF8C33",  # Orange
        ]

        columns = [] if columns is None else columns
        num_colors = len(default_palette)
        color_map = {}

        for i, column in enumerate(columns):
            color_index = i % num_colors
            color_map[column] = default_palette[color_index]

        return cls(color_map)

    def get_edges(self, columns: list[str]) -> set[str]:
        edge_colors = {self.get_edge(column) for column in columns}
        non_default_edges = edge_colors.difference({self.DEFAULT_EDGE_COLOR})
        if len(non_default_edges) == 0:
            return edge_colors
        return non_default_edges

    def get_edge(self, column: str) -> str:
        return self.color_map.get(column, self.DEFAULT_EDGE_COLOR)

    def get_cell(self, column: str) -> str:
        return self.color_map.get(column, self.DEFAULT_CELL_COLOR)


def draw_dag(
    graph: nx.DiGraph[str],
    *,
    colors: ColorProvider = NodeColors(),
    title: str = "Dataflow DAG",
) -> Figure:
    fig = plt.figure(figsize=(28.0, 12.0))
    ax = fig.add_subplot()
    pos = nx.nx_pydot.graphviz_layout(graph, prog="dot")
    nx.draw_networkx(
        graph,
        pos,
        ax=ax,
        with_labels=True,
        node_size=500,
        node_color=colors(graph),
        edge_color="gray",
        font_size=5,
        font_weight="bold",
        arrows=True,
    )

    ax.set_title(title)

    return fig


def view_dag_with_columns(
    graph: nx.DiGraph[str],
    *,
    colors: ColumnColorProvider,
    title: str = "Dataflow DAG",
    columns_to_show: list[str] | None = None,
) -> None:
    s = graphviz.Digraph(title, node_attr={"shape": "plaintext"})
    for node, node_data in graph.nodes(data="schema", default={}):
        node_name = str(node)
        # The graph node data is untyped; `create_graph` sets the table schema.
        node_schema = cast(dict[str, str], node_data)
        node_html = (
            GraphvizHtml.header_only(node_name)
            if graph.in_degree[node] == 0
            else GraphvizHtml.with_columns(
                node_name, node_schema, colors, columns_to_show
            )
        )
        s.node(node, node_html)

    for u, v, c in graph.edges(data="common_columns", default=set()):
        if len(c) == 0:
            s.edge(u, v)  # No common edges, draw a single default-colored edge
            continue

        common_columns = list(map(str, c))
        for edge_color in colors.get_edges(common_columns):
            s.edge(u, v, color=edge_color)

    s.view()


@frozen
class GraphvizHtml:
    @frozen
    class _Column:
        name: str
        data_type: str
        color: str | None

        def to_html(self) -> str:
            inner_html = f"{self.name}: {html.escape(self.data_type)}"
            color_html = f" bgcolor='{self.color}'" if self.color else ""
            return f"<tr><td align='left'{color_html}>{inner_html}</td></tr>"

    @staticmethod
    def _header(name: str) -> str:
        return f"<tr><td><b>{name}</b></td></tr>"

    @staticmethod
    def _body(columns: list[GraphvizHtml._Column]) -> str:
        return "\n".join([col.to_html() for col in columns])

    @staticmethod
    def header_only(name: str) -> str:
        return f'<<table border="0" cellborder="0" cellspacing="0">{GraphvizHtml._header(name)}</table>>'

    @staticmethod
    def with_columns(
        name: str,
        schema: dict[str, str],
        color_column: ColumnColorProvider,
        columns_to_show: list[str] | None = None,
    ) -> str:
        def keep_column(column: str) -> bool:
            if columns_to_show is None:
                return True
            return column in columns_to_show

        columns = [
            GraphvizHtml._Column(data_name, data_type, color_column.get_cell(data_name))
            for data_name, data_type in schema.items()
            if keep_column(data_name)
        ]

        return f"""<<table border="0" cellborder="1" cellspacing="0">
    {GraphvizHtml._header(name)}
    {GraphvizHtml._body(columns)}
</table>>"""
