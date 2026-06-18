"""Generate IbisSchema classes for Expression classes.

Example usage:
    python -m ibis_typing.schemagen \
        my_package.expressions \
        --schema-package my_package.generated.schemas \
        --schema-suffix Schema \
        --write
"""

import argparse
import difflib
import importlib
import sys
from types import ModuleType

from attrs import frozen

from ibis_typing.schema_bindings import SuffixNameProvider

from .. import schema_writer


@frozen
class Args:
    expr_package: ModuleType
    schema_package: ModuleType
    schema_suffix: str
    write: bool


def parse_args(argv=None) -> Args:
    parser = argparse.ArgumentParser()
    arg = parser.add_argument

    arg(
        "expr_package",
        type=importlib.import_module,
        help="Package with input Expression classes",
    )
    arg(
        "--schema-package",
        type=importlib.import_module,
        help="Package for output IbisSchema classes",
        required=True,
    )
    arg(
        "--schema-suffix",
        help="Name suffix for output IbisSchema classes",
        default="Schema",
    )
    arg(
        "--write",
        action="store_true",
        help="Write output to file. Otherwise, print to stdout.",
    )

    return Args(**vars(parser.parse_args(argv)))


def main(argv=None):
    args = parse_args(argv)

    print(
        f"Generating schemas for {args.expr_package.__name__} to {args.schema_package.__name__}",
        file=sys.stderr,
    )

    name_provider = SuffixNameProvider(args.schema_suffix)
    expr_to_schema_package = dict.fromkeys(
        schema_writer.list_expressions_in_package(args.expr_package),
        args.schema_package,
    )

    current = schema_writer.read_schemas(expr_to_schema_package)
    new = schema_writer.generate_schemas(expr_to_schema_package, name_provider)

    for path, content in new:
        prior = current.get(path)
        diff_lines = difflib.unified_diff(
            content.splitlines(keepends=True),
            (prior or "").splitlines(keepends=True),
            fromfile=f"a/{path}",
            tofile=f"b/{path}",
        )
        diff = "".join(diff_lines)
        if diff:
            print(diff)
        else:
            print(f"{path} (no changes)", file=sys.stderr)

        if args.write:
            path.write_text(content)


if __name__ == "__main__":
    main()
