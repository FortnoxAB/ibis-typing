"""
Rewrite ibis.* calls to ibis_typing @ expressions.

Refactoring script: ibis API calls → ibis_typing ExtensionMethod (@-operator) calls.

Uses LibCST for AST-level rewrites and rope for project-wide file discovery.

Usage
-----
# Dry-run (print diffs, write nothing):
    python -m ibis_typing.refactor /path/to/project

# Apply changes in-place:
    python -m ibis_typing.refactor /path/to/project --apply

# Single file:
    python -m ibis_typing.refactor /path/to/project --file src/foo.py --apply
"""

from __future__ import annotations

import argparse
from argparse import Namespace
from pathlib import Path

from rope.base.project import Project
from rope.base.resources import File

from ibis_typing.refactor.migrations import MIGRATIONS

from . import writer


def parse_args(argv: list[str] | None) -> Namespace:
    parser = argparse.ArgumentParser(description=__doc__)

    arg = parser.add_argument
    arg("project", help="Path to the rope project root")
    arg(
        "--apply",
        action="store_true",
        help="Write changes (default: dry-run / diff only)",
    )
    arg(
        "--file",
        metavar="PATH",
        help="Restrict to a single file instead of the whole project",
    )
    arg(
        "--module",
        nargs="+",
        default=tuple(MIGRATIONS),
        help="API module to migrate.",
        choices=tuple(MIGRATIONS),
    )

    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)

    apply = args.apply
    project = Project(args.project)
    transformers = [MIGRATIONS[m] for m in args.module]

    files = (
        [Path(args.file)]
        if args.file
        else [
            Path(args.project) / res.path
            for res in project.get_files()
            if isinstance(res, File) and res.path.endswith(".py")
        ]
    )

    changed_files = sum(
        writer.rewrite_file(t, f, apply=apply) for f in files for t in transformers
    )

    action = "applied" if apply else "would change"
    print(f"\n{action}: {changed_files} / {len(files)} file(s)")

    if not apply and changed_files:
        print("Re-run with --apply to write changes.")

    project.close()


if __name__ == "__main__":
    main()
