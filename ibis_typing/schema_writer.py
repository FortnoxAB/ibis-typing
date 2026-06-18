"""Write .py modules for generated `IbisSchema`s of `Expression` classes."""

import functools
import importlib
import logging
from collections.abc import Iterable, Mapping
from pathlib import Path
from types import ModuleType
from typing import cast

from . import evaluator, schema_bindings
from .expression import Expression
from .plot import graph
from .schema_bindings import NameProvider, SuffixNameProvider
from .table_provider import AbstractTableProvider, TableProviders, get_abstract_table

NamedModules = Mapping[str, str]
ExprToSchemaPackage = Mapping[type[Expression], ModuleType]
SchemaImpl = tuple[Path, str]

logger = logging.getLogger(__name__)


def generate_schemas_with_diff_check(
    expr_to_schema_package: ExprToSchemaPackage,
    update_expected: bool = False,
    name_provider: NameProvider = SuffixNameProvider(),
) -> None:
    """Write schemas or check that they are unchanged."""
    current = read_schemas(expr_to_schema_package)

    def iter_schemas():
        for path, content in generate_schemas(expr_to_schema_package, name_provider):
            yield path, content
            if content == (prior := current.get(path)):
                continue

            if update_expected:
                path.write_text(content)
            else:
                assert content == prior, f"Schema differ from prior: {path.name}"

    new = dict(iter_schemas())
    assert set(new) == set(current), "Schema set differ from prior"


def read_schemas(expr_to_schema_package: ExprToSchemaPackage) -> dict[Path, str]:
    return {
        as_module_path(name, schema_package): content
        for schema_package in set(expr_to_schema_package.values())
        for name, content in read_package_modules(schema_package).items()
    }


def generate_schemas(
    expr_to_schema_package: ExprToSchemaPackage,
    name_provider: NameProvider = SuffixNameProvider(),
) -> Iterable[SchemaImpl]:
    """Generate IbisSchema modules for given Expressions.

    1. Generate IbisSchema for Expressions in topological DAG order.
        Reuse generated Expressions as inputs to dependent Expressions.
    2. Generate package index modules for all schema packages involved.
    """
    expr_to_schema_package = {
        expr: expr_to_schema_package[expr]
        for expr in graph.get_expression_dag(expr_to_schema_package)
        if expr in expr_to_schema_package
    }

    tables = {}
    providers: TableProviders = cast(TableProviders, [tables.get, get_abstract_table])

    for expr, schema_package in expr_to_schema_package.items():
        logger.info(f"Generating schema for {expr.__name__}")
        table = evaluator.from_expression(expr, table_providers=providers)

        # Make available for dependent Expressions
        tables[expr] = AbstractTableProvider.from_reference(table)
        name, content = schema_bindings.create_package_module(table, name_provider)
        path = as_module_path(name, schema_package)

        yield path, content

    for schema_package in get_schema_packages(expr_to_schema_package):
        logger.info(f"Generating schema index for {schema_package.__name__}")
        schemas = read_package_modules(schema_package)

        name, content = schema_bindings.create_package_index(schemas)
        path = as_module_path(name, schema_package)

        yield path, content


def get_schema_packages(expr_to_package: ExprToSchemaPackage) -> set[ModuleType]:
    return set(expr_to_package.values())


@functools.lru_cache
def get_package_path(package: ModuleType) -> Path:
    return Path(cast(str, package.__file__)).parent


def as_module_path(name: str, package: ModuleType) -> Path:
    return (get_package_path(package) / name).with_suffix(".py")


def read_package_modules(package: ModuleType) -> NamedModules:
    return {
        module.stem: module.read_text()
        for module in get_package_path(package).iterdir()
        if module.suffix == ".py"
    }


def list_expressions_in_package(
    package: ModuleType, *, expression_base: type[Expression] = Expression
) -> set[type[Expression]]:
    return {
        expression
        for module in iter_submodules(package)
        for expression in list_expressions_in_module(
            module, expression_base=expression_base
        )
    }


def list_expressions_in_module(
    module: ModuleType, *, expression_base: type[Expression] = Expression
) -> set[type[Expression]]:
    return {
        expression
        for name in dir(module)
        if isinstance((expression := getattr(module, name)), type)
        if issubclass(expression, expression_base)
        if expression.__module__.startswith(module.__name__)
    }


def iter_submodules(package: ModuleType) -> Iterable[ModuleType]:
    package_path = Path(str(package.__file__)).parent
    for module_path in package_path.rglob("*.py"):
        rel_path = module_path.relative_to(package_path)
        if "tests" in rel_path.parts:
            continue
        module_name = rel_path.as_posix().replace("/", ".")[:-3]
        yield importlib.import_module(package.__name__ + "." + module_name)
