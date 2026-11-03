"""Type patchers rewrite ibis module source."""

import pytest

from ibis_typing.type_patch.patchers import MethodParameterTypePatcher

WIDENED = "tuple[str, str] | str | None"


class Backend:
    def drop_view(self, name: str, *, database: str | None = None) -> None: ...


MODULE = """
class Backend:
    @overload
    def drop_view(self, name: str, *, database: str | None = None) -> None: ...
    def drop_view(self, name, *, database=None):
        database: str | None = None


class Other:
    def drop_view(self, name: str, *, database: str | None = None) -> None: ...
"""


def test_method_parameter_type_patcher_widens_the_annotated_definitions():
    patcher = MethodParameterTypePatcher(Backend.drop_view, "database", WIDENED)

    patched = patcher(MODULE)

    assert patched == MODULE.replace(
        "def drop_view(self, name: str, *, database: str | None = None)",
        f"def drop_view(self, name: str, *, database: {WIDENED} = None)",
        1,
    )


def test_method_parameter_type_patcher_rejects_an_unknown_parameter():
    patcher = MethodParameterTypePatcher(Backend.drop_view, "catalog", WIDENED)

    with pytest.raises(LookupError, match=r"Backend\.drop_view"):
        patcher(MODULE)
