"""Argument parsing shared by the plot command line tools."""

from __future__ import annotations

import importlib

from ibis_typing import Expression


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
