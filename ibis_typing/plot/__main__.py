from __future__ import annotations

import argparse
import json
import logging
from collections.abc import Mapping, Sequence
from pathlib import Path

from attrs import frozen

from ibis_typing import Expression, expression_dag
from ibis_typing.plot import cli, graph

logger = logging.getLogger(__name__)


def main(argv: Sequence[str] | None = None):
    logging.basicConfig(level=logging.INFO)
    args = parse_args(argv)

    logger.info("Generating DAG for %s", args.tables)
    colors = graph.NodeColors(args.color_by_name or {})

    dag_structure = expression_dag.get_expression_dag(args.tables)
    dag = graph.create_graph(dag_structure)
    fig = graph.draw_dag(dag, colors=colors)

    logger.info("Saving DAG to %s", args.output)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.output, dpi=300, bbox_inches="tight")


@frozen
class Params:
    tables: Sequence[type[Expression]]
    output: Path
    color_by_name: Mapping[str, str] | None = None


def parse_args(argv: Sequence[str] | None = None) -> Params:
    parser = argparse.ArgumentParser(description=__doc__)
    arg = parser.add_argument

    arg(
        "tables",
        type=cli.import_expression_by_name,
        nargs="+",
        help="List of fully qualified Expression names to include in the DAG.",
    )
    arg(
        "--output",
        type=Path,
        default=Path("output/dag.png"),
        help="Output path for the generated DAG image.",
    )
    arg(
        "--color-by-name",
        type=json.loads,
        help="JSON of text-to-color map for matching node names.",
    )

    return Params(**vars(parser.parse_args(argv)))


if __name__ == "__main__":
    main()
