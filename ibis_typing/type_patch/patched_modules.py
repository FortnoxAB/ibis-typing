"""Index of type-patched modules."""

import _pytest.monkeypatch
import ibis.backends
import ibis.backends.sql
import ibis.backends.trino
import ibis.expr.api
import ibis.expr.types.arrays
import ibis.expr.types.generic
import ibis.expr.types.json
import ibis.expr.types.logical
import ibis.expr.types.maps
import ibis.expr.types.numeric
import ibis.expr.types.relations
import ibis.expr.types.rich

from . import (
    api,
    backends,
    generic,
    logical,
    monkeypatch,
    numeric,
    relations,
    rich,
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
            ibis.expr.types.rich,
            rich.get_patchers(),
        ),
        PatchedModuleWriter(
            ibis.backends,
            backends.get_base_patchers(),
        ),
        PatchedModuleWriter(
            ibis.backends.sql,
            backends.get_sql_patchers(),
        ),
        PatchedModuleWriter(
            ibis.backends.trino,
            backends.get_trino_patchers(),
        ),
        PatchedModuleWriter(
            _pytest.monkeypatch,
            monkeypatch.get_patchers(),
        ),
    ]
