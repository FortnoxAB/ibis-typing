"""Index of type-patched modules."""

import _pytest.monkeypatch
import ibis.expr.api
import ibis.expr.types.arrays
import ibis.expr.types.generic
import ibis.expr.types.json
import ibis.expr.types.logical
import ibis.expr.types.maps
import ibis.expr.types.numeric
import ibis.expr.types.relations

from . import (
    api,
    generic,
    logical,
    monkeypatch,
    numeric,
    relations,
)
from .patchers import PatchedModuleWriter


def get_patched_module_writers():
    return [
        PatchedModuleWriter(
            ibis.expr.api,
            api.get_patchers(),
        ),
        PatchedModuleWriter(
            ibis.expr.types.generic,
            generic.get_patchers(),
        ),
        PatchedModuleWriter(
            ibis.expr.types.logical,
            logical.get_patchers(),
        ),
        PatchedModuleWriter(
            ibis.expr.types.numeric,
            numeric.get_patchers(),
        ),
        PatchedModuleWriter(
            ibis.expr.types.relations,
            relations.get_patchers(),
        ),
        PatchedModuleWriter(
            _pytest.monkeypatch,
            monkeypatch.get_patchers(),
        ),
    ]
