import argparse
from collections.abc import Sequence

from attrs import frozen

from ibis_typing.expression import Expression
from ibis_typing.plot import graph


def main(argv=None) -> None:
    args = parse_args(argv)

    dag_structure = graph.get_expression_dag(args.tables)
    if args.filter:
        dag_structure = graph.filter_dag_on_column(
            args.tables[0], dag_structure, args.filter
        )

    dag = graph.create_graph(dag_structure)

    graph.view_dag_with_columns(
        dag,
        colors=graph.ColumnColorProvider.with_default_colors(args.highlight),
        columns_to_show=None if args.show_all else args.highlight,
    )


@frozen
class Params:
    tables: Sequence[type[Expression]]
    filter: str | None = None
    highlight: list[str] | None = None
    show_all: bool | None = None


def parse_args(argv=None) -> Params:
    parser = argparse.ArgumentParser(description=__doc__)
    arg = parser.add_argument

    arg(
        "tables",
        type=graph.import_expression_by_name,
        nargs="+",
        help="List of fully qualified Expression names to include in the DAG.",
    )
    arg(
        "--filter",
        type=str,
        help="Filter out a subtree of ancestors to the provided tables containing a column name",
        required=False,
    )
    arg(
        "--highlight",
        type=str,
        nargs="+",
        help="Visually highlight these columns in the graph",
        required=False,
    )
    arg(
        "--show-all",
        help="Show all columns in the graph",
        action="store_true",
        required=False,
    )

    return Params(**vars(parser.parse_args(argv)))


if __name__ == "__main__":
    main()
