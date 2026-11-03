"""Patched ibis array callbacks accept functions typed over the element type.

The calls below are checked statically against the patched ibis module and at
runtime against the real signatures through `mock.create_autospec`.
"""

import functools
import inspect
from unittest import mock

import ibis.expr.types.arrays
from ibis import ir

from ibis_typing.ibis_ops import JsonFormat
from ibis_typing.type_patch import arrays


def is_object(value: ir.JSONValue) -> ir.BooleanValue:
    return value["name"].str.notnull()


def test_array_map_and_filter_accept_element_typed_callbacks():
    mocked = mock.create_autospec(ir.ArrayValue, instance=True)
    array: ir.ArrayValue = mocked

    format_json = JsonFormat().apply

    array.map(format_json)
    array.filter(is_object)

    assert mocked.mock_calls == [
        mock.call.map(format_json),
        mock.call.filter(is_object),
    ]


def test_array_patchers_add_overloads_to_the_installed_module_source():
    patchers = arrays.get_patchers()
    source = inspect.getsource(ibis.expr.types.arrays)

    patched = functools.reduce(lambda impl, patch: patch(impl), patchers, source)

    assert "def map(self, func: Callable[[Any], ir.Value], /)" in patched
    assert "predicate: Callable[[Any], bool | ir.BooleanValue]" in patched
