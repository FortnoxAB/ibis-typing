"""Generate Python code for IbisSchema for Expression classes."""

import subprocess
import sys
from collections.abc import Iterable
from typing import Protocol

import ruff
from attrs import frozen
from ibis.expr import datatypes

from ibis_typing.expression import Expression

from . import naming
from .ibis_adapter import IbisTable


class NameProvider(Protocol):
    def __call__(self, expression: type[Expression]) -> str: ...


@frozen
class SuffixNameProvider(NameProvider):
    suffix: str = ""

    def __call__(self, expression: type[Expression]) -> str:
        return expression.__name__ + self.suffix


def create_package_index(modules: Iterable[str]) -> tuple[str, str]:
    name = "__init__"
    sorted_modules = sorted(module for module in modules if module != name)
    content = create_ibis_bindings_package_index(sorted_modules)
    return name, content


def create_package_module(
    table: IbisTable[Expression], name_provider: NameProvider
) -> tuple[str, str]:
    name = naming.snake_case(name_provider(table.table_schema))
    content = create_ibis_bindings_module([table], name_provider)
    return name, content


def create_ibis_bindings_package_index(modules: list[str]) -> str:
    """Generate a package index file for a collection of modules.

    >>> print(create_ibis_bindings_package_index(["module1", "module2"]))
    # noqa
    from .module1 import *
    from .module2 import *
    <BLANKLINE>
    """
    noqa = "# noqa\n"
    raw = ";".join(f"from .{module} import *" for module in modules)
    return format_py(noqa + raw)


def create_ibis_bindings_module(
    tables: list[IbisTable[Expression]],
    name_provider: NameProvider = SuffixNameProvider(),
) -> str:
    """Generate bindings modules for a collection of tables.

    >>> from attrs import frozen
    >>> from ibis_typing import IbisSchema
    >>> from ibis_typing.ibis_types import Date, Int32

    >>> @frozen
    ... class MyTable(IbisSchema):
    ...     month: Date = None
    ...     import_job_id: Int32 = None

    >>> ibis_table = MyTable.of_rows([])
    >>> module = create_ibis_bindings_module([ibis_table])
    >>> print(module)
    from attrs import frozen
    from ibis_typing import IbisSchema
    from ibis_typing.ibis_types import *
    <BLANKLINE>
    __all__ = [
        "MyTable",
    ]
    <BLANKLINE>
    <BLANKLINE>
    @frozen
    class MyTable(IbisSchema):
        month: Date = None
        import_job_id: Int32 = None
    <BLANKLINE>
        table_schema = {
            "month": "date",
            "import_job_id": "int32",
        }
    <BLANKLINE>
    """
    ordered = sorted(tables, key=lambda t: name_provider(t.table_schema))
    class_codes = [create_table_dataclass(table, name_provider) for table in ordered]
    module_headers = [
        "from attrs import frozen",
        "from ibis_typing import IbisSchema",
        "from ibis_typing.ibis_types import *",
    ]
    export_declaration = [
        "__all__ = [",
        *(f'"{name_provider(t.table_schema)}",' for t in ordered),
        "]",
    ]
    complete_module_raw = "\n".join(
        [*module_headers, *export_declaration, *class_codes]
    )
    complete_module = format_py(complete_module_raw)
    return complete_module


def create_table_dataclass(
    table: IbisTable[Expression], name_provider: NameProvider
) -> str:
    class_name = name_provider(table.table_schema)
    schema = table.table.schema()
    fields = [
        f"{naming.safe_name(name)}: {ibis_type_annotation(data_type)} = None"
        for name, data_type in schema.items()
    ]
    columns = [f"{name!r}: {str(data_type)!r}," for name, data_type in schema.items()]
    fields_code = ";".join(fields)
    columns_code = "{" + "".join(columns) + "}"
    class_code = f"""
@frozen
class {class_name}(IbisSchema):
    {fields_code}

    table_schema = {columns_code}
"""

    return class_code


def ibis_type_annotation(data_type: datatypes.DataType) -> str:
    """Generate a type annotation for an ibis datatype.

    >>> ibis_type_annotation(datatypes.Int32())
    'Int32'
    >>> ibis_type_annotation(datatypes.Array(datatypes.Int32()))
    'Array[Int32]'
    >>> ibis_type_annotation(datatypes.Map(datatypes.Int32(), datatypes.String()))
    'Map[Int32, String]'
    """

    return f"{data_type.__class__.__name__}{get_type_param_suffix(data_type)}"


def get_type_param_suffix(data_type: datatypes.DataType) -> str:
    match data_type:
        case datatypes.Array():
            return f"[{data_type.value_type.__class__.__name__}]"
        case datatypes.Map():
            return f"[{data_type.key_type.__class__.__name__}, {data_type.value_type.__class__.__name__}]"
        case _:
            return ""


def format_py(source: str) -> str:
    return subprocess.check_output(
        [sys.executable, "-m", ruff.__name__, "format", "-"],
        input=source,
        encoding="utf-8",
    )
