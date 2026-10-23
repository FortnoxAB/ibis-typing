"""Provides name transforms for classes and fields."""

import keyword
import re


def class_name(name: str) -> str:
    """Create PascalCase python class name.

    >>> class_name("class")
    'Class'
    >>> class_name("1onE")
    'D1One'
    """
    return safe_name(pascal_case(name), number_prefix="D")


def pascal_case(name: str) -> str:
    """Transform snake_case to PascalCase.

    >>> pascal_case("my__snake_case")
    'MySnakeCase'
    """
    return "".join(part.title() for part in re.split(r"[^a-zA-Z0-9]", name))


def snake_case(name: str) -> str:
    """Transform other cases to snake_case.

    >>> snake_case("snakeCase")
    'snake_case'
    >>> snake_case("SnakeCase")
    'snake_case'
    """
    return re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()


def safe_name(name: str, number_prefix: str = "d") -> str:
    """Create safe Python names.

    >>> safe_name("safe_name")
    'safe_name'
    >>> safe_name("123_digit_name")
    'd123_digit_name'
    >>> safe_name("dashed-name")
    'dashedname'
    >>> safe_name("class")  # Suffix keywords with underscores
    'class_'
    >>> safe_name("self")  # Suffix protected field names with underscores
    'self_'
    """
    # Still allow "type" as a field name
    softkwlist = set(keyword.softkwlist) - {"type"}
    protected_field_names = ["self", *keyword.kwlist, *softkwlist]

    name = re.sub(r"\W", "", name)
    if name[0].isdigit():
        return safe_name(number_prefix + name)
    if name in protected_field_names:
        return safe_name(name + "_")
    return name
