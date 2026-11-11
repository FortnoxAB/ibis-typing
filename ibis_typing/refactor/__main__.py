"""
Rewrite ibis.* calls to ibis_typing @ expressions.

Refactoring script: ibis API calls → ibis_typing ExtensionMethod (@-operator) calls.

Uses LibCST for AST-level rewrites and pathlib for project-wide file discovery.

Usage
-----
# Dry-run (print diffs, write nothing):
    python -m ibis_typing.refactor /path/to/project

# Apply changes in-place:
    python -m ibis_typing.refactor /path/to/project --apply

# Single file:
    python -m ibis_typing.refactor /path/to/project/file.py --apply

# Table method chains (opt-in; Ibis code only):
    python -m ibis_typing.refactor /path/to/project --module table
"""

from __future__ import annotations

import argparse
from argparse import Namespace
from pathlib import Path

from ibis_typing.refactor.migrations import DEFAULT_MIGRATIONS, MIGRATIONS

from . import writer


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    transformers = [MIGRATIONS[m] for m in args.module]
    files = _select_files(args)

    changed_files = sum(
        writer.rewrite_file(t, f, apply=args.apply) for f in files for t in transformers
    )

    action = "applied" if args.apply else "would change"
    print(f"\n{action}: {changed_files} / {len(files)} file(s)")

    if not args.apply and changed_files:
        print("Re-run with --apply to write changes.")


def parse_args(argv: list[str] | None) -> Namespace:
    parser = argparse.ArgumentParser(description=__doc__)

    arg = parser.add_argument
    arg("project", type=Path, help="Path to the project root")
    arg(
        "--apply",
        action="store_true",
        help="Write changes (default: dry-run / diff only)",
    )
    arg(
        "--file",
        metavar="PATH",
        type=Path,
        help="Restrict to a single file instead of the whole project",
    )
    arg(
        "--module",
        nargs="+",
        default=DEFAULT_MIGRATIONS,
        help="API module to migrate.",
        choices=tuple(MIGRATIONS),
    )

    return parser.parse_args(argv)


def _select_files(args: Namespace) -> list[Path]:
    if args.file:
        return [args.file]
    return sorted(args.project.rglob("*.py"))


if __name__ == "__main__":
    main()
