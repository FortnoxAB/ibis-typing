"""Type patches for ibis.expr.types.rich."""

from __future__ import annotations

from .patchers import SourceReplacePatcher

__all__ = ["get_patchers"]

# Type checkers merge both conditional FixedTextJupyterMixin definitions
# into an unknown base class of Column and Table,
# which makes any attribute and `@` operator on them Unknown.
# Hide the fallback without rich from type checkers.
_FALLBACK = '''except ImportError:

    class FixedTextJupyterMixin:
        """No-op when rich is not installed."""
'''
_TYPED_FALLBACK = '''except ImportError:
    if not TYPE_CHECKING:

        class FixedTextJupyterMixin:
            """No-op when rich is not installed."""
'''


def get_patchers():
    return [SourceReplacePatcher(_FALLBACK, _TYPED_FALLBACK)]
