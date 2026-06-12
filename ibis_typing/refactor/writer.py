import difflib
from pathlib import Path

import libcst as cst


def rewrite_file(self: cst.CSTTransformer, path: Path, apply: bool) -> bool:
    """Rewrite a single file. Returns True if changes were made."""
    source = path.read_text(encoding="utf-8")
    tree = cst.parse_module(source)
    new_tree = tree.visit(self)
    new_source = new_tree.code

    if tree.code == new_tree.code:
        return False

    diff = difflib.unified_diff(
        source.splitlines(keepends=True),
        new_source.splitlines(keepends=True),
        fromfile=f"a/{path}",
        tofile=f"b/{path}",
    )
    print("".join(diff), end="")

    if apply:
        path.write_text(new_source, encoding="utf-8")
        print(f"  ✓ written: {path}")

    return True
