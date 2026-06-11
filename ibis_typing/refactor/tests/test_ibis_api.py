import textwrap

import libcst as cst

from ibis_typing.refactor.rewrite_call import ibis_api_transformer


def rewrite_source(source: str) -> str:
    self = ibis_api_transformer
    tree = cst.parse_module(source)
    new_tree = tree.visit(self)
    return new_tree.code


def rewrite(src: str) -> str:
    source = textwrap.dedent(src).strip()
    return rewrite_source(source).replace("from ibis_typing import it", "").strip()


def test_desc_no_kwargs():
    result = rewrite("ibis.desc(col)")
    assert result == "col @ it.Desc()"


def test_desc_with_nulls_first():
    result = rewrite("ibis.desc(col, nulls_first=True)")
    assert result == "col @ it.Desc(nulls_first=True)"


def test_ifelse():
    result = rewrite("ibis.ifelse(cond, then_val, else_val)")
    assert result == "cond @ it.IfElse(then_val, else_val)"


def test_cases():
    src = "ibis.cases((a, b), (c, d), else_=default)"
    result = rewrite(src)
    assert result == "default @ it.Cases((a, b), (c, d))"


def test_cases_single_pair():
    result = rewrite("ibis.cases((x, y), else_=z)")
    assert result == "z @ it.Cases((x, y))"


def test_coalesce_single_fallback():
    result = rewrite("ibis.coalesce(val, fallback)")
    assert result == "val @ it.FillNull(fallback)"


def test_coalesce_multiple():
    result = rewrite("ibis.coalesce(a, b, c)")
    assert result == "a @ it.FillNull(b, c)"


def test_greatest():
    result = rewrite("ibis.greatest(a, b, c)")
    assert result == "a @ it.Greatest(b, c)"


def test_least():
    result = rewrite("ibis.least(x, y)")
    assert result == "x @ it.Least(y)"


def test_and():
    result = rewrite("ibis.and_(p, q, r)")
    assert result == "p @ it.And(q, r)"


def test_or():
    result = rewrite("ibis.or_(p, q)")
    assert result == "p @ it.Or(q)"


def test_import_injected_when_missing():
    src = "import ibis\n\nibis.and_(x, y)\n"
    out = rewrite_source(src)
    assert "from ibis_typing import it" in out
    assert "x @ it.And(y)" in out


def test_non_ibis_call_untouched():
    src = "foo.desc(x)"
    out = rewrite_source(src)
    assert out.strip() == src


def test_unknown_ibis_call_untouched():
    src = "ibis.table('my_table')"
    _out = rewrite_source(src)


def test_nested_calls():
    src = "ibis.ifelse(ibis.and_(a, b), x, y)"
    out = rewrite_source(src)
    assert "@ it.IfElse" in out
    assert "@ it.And" in out
