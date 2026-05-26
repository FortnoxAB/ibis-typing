from __future__ import annotations

import abc
import functools
import typing
from collections.abc import Mapping
from typing import cast

import attrs
import ibis
from attrs import frozen

from .ibis_adapter import IbisSchema, IbisTable
from .table_provider import get_abstract_table


class Expression(IbisSchema, abc.ABC):
    """Class-based `IbisTable` transform.

    Any input `IbisTable` expression that subclass `Expression`
    will be provided by the specific constructor of those expressions.
    This is essentially injected default arguments in a function signature.
    """

    @classmethod
    @abc.abstractmethod
    def from_expression[T: Expression](cls: type[T], *args, **kwargs) -> IbisTable[T]:
        """Compose the ibis.Table for the (IbisTable, ...) -> IbisTable transform."""

    @classmethod
    def get_parameter_schema_types(cls) -> Mapping[str, type[IbisSchema]]:
        """Override for dynamic declaration of schema types."""
        return get_parameter_schema_types(cls.from_expression)

    @classmethod
    def _get_table_schema(cls) -> Mapping[str, str]:
        """Generate the ibis schema for the expression."""
        return generate_table_schema(
            cls.from_expression, cls.get_parameter_schema_types()
        )


class GenericExpression(Expression, abc.ABC):
    """Expression with a specified generic table expression."""

    @classmethod
    @abc.abstractmethod
    def get_table_expression(cls) -> TableExpression:
        """Provides the implementation of the generic expression."""
        ...

    @classmethod
    def from_expression[S: GenericExpression](
        cls: type[S], *args, **kwargs
    ) -> IbisTable[S]:
        expr = cls.get_table_expression()
        table = expr(*args, **kwargs)
        schema = cast(type[S], expr.output_schema) or cls
        return schema.of(table)

    @classmethod
    def get_parameter_schema_types(cls) -> Mapping[str, type[IbisSchema]]:
        return cls.get_table_expression().input_schemas


@frozen
class TableExpression(abc.ABC):
    """Describes a generalized ibis.Table expression function."""

    @abc.abstractmethod
    def __call__(self, *args, **kwargs) -> ibis.Table:
        """A typed IbisTable -> ibis.Table transform.

        BoundIbisExpression wraps the output as an IbisTable.
        """

    @property
    def input_schemas(self) -> Mapping[str, type[IbisSchema]]:
        """Input schemas to the expression."""
        return get_parameter_schema_types(self.__call__)

    @property
    def output_schema(self) -> type[IbisSchema] | None:
        """Declared output schema of the expression, if available."""
        return None

    @property
    def generated_class_name(self) -> str:
        """Name of generated ParametricExpression IbisSchema class."""
        return type(self).__name__

    @functools.lru_cache
    def as_expression_schema[E: GenericExpression](self) -> type[E]:
        """Generate a new ParametricExpression IbisSchema class."""
        schema = generate_table_schema(self, self.input_schemas)
        ret = attrs.make_class(
            name=self.generated_class_name,
            attrs=list(schema),
            bases=(GenericExpression,),
            class_body={
                "get_table_expression": lambda: self,
                "table_schema": schema,
            },
            frozen=True,
            slots=True,
        )
        return cast(type[E], ret)


@frozen
class SingleInputTableExpression[S: IbisSchema](TableExpression, abc.ABC):
    origin: type[S]

    @property
    def input_schemas(self):
        return {"origin": self.origin}


@frozen
class IdentityTableExpression(SingleInputTableExpression, abc.ABC):
    @property
    def output_schema(self):
        return self.origin


def generate_table_schema(from_expression, schemas) -> dict[str, str]:
    inputs = {name: get_abstract_table(schema) for name, schema in schemas.items()}
    ret = from_expression(**inputs)
    table = ret.table if isinstance(ret, IbisTable) else ret
    return {column: str(ibis_type) for column, ibis_type in table.schema().items()}


def get_parameter_schema_types(fun: typing.Callable) -> Mapping[str, type[IbisSchema]]:
    """Get the IbisSchema types from the function signature.

    >>> from ibis_typing import IbisTable, IbisSchema

    >>> class MySchema(IbisSchema): ...
    >>> def transform(input_table: IbisTable[MySchema]) -> IbisTable[...]: ...
    >>> def transform_deferred_types(input_table: "IbisTable[MySchema]"): ...

    >>> get_parameter_schema_types(transform)
    {'input_table': <class 'ibis_typing.expression.MySchema'>}

    >>> get_parameter_schema_types(transform_deferred_types)
    {'input_table': <class 'ibis_typing.expression.MySchema'>}
    """
    return {
        name: typing.get_args(param)[0]
        for name, param in typing.get_type_hints(fun).items()
        if name not in ("cls", "self", "return")
    }
