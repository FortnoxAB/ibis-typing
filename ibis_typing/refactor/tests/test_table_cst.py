from __future__ import annotations

from typing import Any

import ibis
import libcst
import pytest

from ibis_typing import it, this
from ibis_typing.refactor.table_cst import TableTransformer


def rewrite_source(source: str) -> str:
    return libcst.parse_module(source).visit(TableTransformer()).code


def rewrite(source: str) -> str:
    """Return the rewritten last line, without the added import."""
    return rewrite_source(source).splitlines()[-1]


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("t.filter(a > 1, b)", "t @ it.deferred.filter(a > 1, b)"),
        ('t.select("a", "b")', 't @ it.Select("a", "b")'),
        ("t.select(a=x, **more)", 't @ it.Select({"a": x, **more})'),
        ("t.select(**more)", "t @ it.Select(more)"),
        ("(t.filter(p))", "(t @ it.deferred.filter(p))"),
        ('t.select("a", this[c.b], n=x)', 't @ it.Select("a", c.b, expr={"n": x})'),
        ('t.join(r, "k")', 't @ it.InnerJoin(r, keys=["k"])'),
        ("t.join(r, [c.k, this[c.j]])", "t @ it.InnerJoin(r, keys=[c.k, c.j])"),
        ('t.join(r, ("k",), how="left")', 't @ it.LeftJoin(r, keys=["k"])'),
        ('t.anti_join(r, "k")', 't @ it.AntiJoin(r, keys=["k"])'),
        ("t.cross_join(r)", "t @ it.InnerJoin(r, keys=[])"),
        (
            't.group_by(this[c.k], "j").aggregate(n=x)',
            't @ it.Aggregate(by=[c.k, "j"], expr={"n": x})',
        ),
        (
            't.group_by(["k"]).aggregate(n=x)',
            't @ it.Aggregate(by=["k"], expr={"n": x})',
        ),
    ],
)
def test_rule(source: str, expected: str) -> None:
    assert rewrite(source) == expected


def test_chain_becomes_one_flow() -> None:
    source = 't.join(r, "k").filter(p).group_by("k").aggregate(n=x)'
    assert rewrite(source) == (
        't @ it.InnerJoin(r, keys=["k"]) @ it.deferred.filter(p)'
        ' @ it.Aggregate(by=["k"], expr={"n": x})'
    )


def test_multiline_flow_keeps_its_parentheses() -> None:
    source = '(\n    t\n    @ it.InnerJoin(r, keys=[])\n).select("a")\n'
    assert rewrite_source(source).endswith(
        '(\n    t\n    @ it.InnerJoin(r, keys=[])\n) @ it.Select("a")\n'
    )


def test_long_chain_stays_one_flat_flow() -> None:
    source = 't.filter(p).select("a").join(r, "a").filter(q).cross_join(s)'
    assert rewrite(source) == (
        't @ it.deferred.filter(p) @ it.Select("a") @ it.InnerJoin(r, keys=["a"])'
        " @ it.deferred.filter(q) @ it.InnerJoin(s, keys=[])"
    )


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("t.filter(p).columns", "(t @ it.deferred.filter(p)).columns"),
        ('t.filter(p)["a"]', '(t @ it.deferred.filter(p))["a"]'),
        ("x @ t.filter(p)", "x @ (t @ it.deferred.filter(p))"),
        ("-t.filter(p)", "-(t @ it.deferred.filter(p))"),
        (
            "t.filter(p).count()",
            "(t @ it.deferred.filter(p)).count()",
        ),
        (
            't.filter(p).select("a").columns',
            '(t @ it.deferred.filter(p) @ it.Select("a")).columns',
        ),
    ],
)
def test_flow_is_parenthesized_in_tighter_contexts(source: str, expected: str) -> None:
    assert rewrite(source) == expected


@pytest.mark.parametrize(
    "source",
    [
        '", ".join(names)',
        "t.join(r, t.a == r.b)",
        't.join(r, "k", how="semi")',
        't.join(r, "k", rname="{name}_r")',
        "t.select(*names)",
        "t.select(t.a + 1)",
        "t.group_by(k).aggregate([x])",
        "t.aggregate(n=x)",
        "t.cross_join(r, lname='{name}_l')",
        "t @ it.deferred.filter(p)",
        't @ it.deferred.select("a", "b")',
    ],
)
def test_other_calls_are_untouched(source: str) -> None:
    assert rewrite_source(source) == source


def test_import_added_once_after_existing_imports() -> None:
    source = '"""Doc."""\n\nimport ibis\n\nt.filter(p)\nt.filter(q)\n'
    assert rewrite_source(source) == (
        '"""Doc."""\n\nimport ibis\nfrom ibis_typing import it\n\n'
        "t @ it.deferred.filter(p)\nt @ it.deferred.filter(q)\n"
    )


def test_existing_import_is_kept() -> None:
    source = "from ibis_typing import it, this\n\nt.filter(p)\n"
    assert rewrite_source(source).count("import") == 1


T = ibis.memtable({"k": [1, 1, 2, 3], "a": [10, 20, 30, 40]})
R = ibis.memtable({"k": [1, 2, 4], "b": ["x", "y", "z"]})


@pytest.mark.parametrize(
    "source",
    [
        "T.filter(this.a > 15)",
        'T.select("a", n=this.a * 2)',
        'T.join(R, "k")',
        'T.join(R, ["k"], how="left").select("k", "a", "b")',
        'T.join(R, "k", how="anti")',
        "T.cross_join(R.select(rk=this.k))",
        'T.group_by("k").aggregate(total=this.a.sum(), n=this.a.count())',
    ],
)
def test_rewrite_returns_the_same_rows(source: str) -> None:
    rewritten = rewrite(source)
    assert rewritten != source
    namespace: dict[str, Any] = {"T": T, "R": R, "it": it, "this": this}
    before = eval(source, namespace)  # parametrized test sources
    after = eval(rewritten, namespace)
    assert _rows(after) == _rows(before)


def _rows(table: ibis.Table) -> list[tuple[tuple[str, object], ...]]:
    """Rows as sorted (column, value) pairs: column order is out of scope."""
    con = ibis.duckdb.connect()
    try:
        rows = con.to_pyarrow(table).to_pylist()
    finally:
        con.disconnect()
    return sorted((tuple(sorted(row.items())) for row in rows), key=repr)
