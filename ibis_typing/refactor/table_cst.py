"""Rewrite Ibis table method chains into ibis-typing `@` flows.

`t.filter(p).group_by("k").aggregate(n=x)` becomes
`t @ it.deferred.filter(p) @ it.Aggregate(by=["k"], expr={"n": x})`.

The rules complement the function rules in `ibis_cst`
(`ibis.least(a, b)` to `a @ it.Least(b)`).

Known differences from the method chains, by design:
`it.Select` and `it.Aggregate` order columns by the input table;
an Expression that needs another order adds `@ it.deferred.select(...)`.
`it.LeftJoin` and `it.OuterJoin` merge the key columns
where Ibis keeps `<key>_right`.

A CST has no types, so the rules match any `.filter(...)`, `.select(...)` etc.
Run them on Ibis code only, never on e.g. Django querysets;
the `table` migration is therefore not run by default.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import override

import libcst
from attrs import define, field, frozen
from libcst.codemod import CodemodContext
from libcst.codemod.visitors import AddImportsVisitor, ImportItem

from ibis_typing.refactor.cst import MatMul, Parenthesize
from ibis_typing.refactor.ibis_cst import CstRule

type TableRule = CstRule[libcst.Call, libcst.BaseExpression]

_JOIN_HOW = {
    "inner": "InnerJoin",
    "left": "LeftJoin",
    "outer": "OuterJoin",
    "anti": "AntiJoin",
}
_STRINGS = (libcst.SimpleString, libcst.ConcatenatedString, libcst.FormattedString)
# Operators that bind as tight as `@` or tighter: a flow operand needs parentheses.
_TIGHT_OPERATORS = (
    libcst.Multiply,
    libcst.Divide,
    libcst.FloorDivide,
    libcst.Modulo,
    libcst.MatrixMultiply,
    libcst.Power,
)


@frozen
class FilterRule(CstRule[libcst.Call, libcst.BaseExpression]):
    """`t.filter(*p)` → `t @ it.deferred.filter(*p)`; the same call, deferred."""

    def apply(self, node: libcst.Call) -> libcst.BaseExpression | None:
        if (table := _receiver(node, "filter")) is None:
            return None
        return _flow(table, _it("deferred", "filter"), node.args)


@frozen
class SelectRule(CstRule[libcst.Call, libcst.BaseExpression]):
    """`t.select("a", b=x)` → `t @ it.Select("a", expr={"b": x})`.

    Keywords only select a dict (`it.Select({"b": x})`),
    which keeps no other column, as `Table.select` does.
    """

    def apply(self, node: libcst.Call) -> libcst.BaseExpression | None:
        if (table := _receiver(node, "select")) is None:
            return None
        if (args := self._args(node.args)) is None:
            return None
        return _flow(table, _it("Select"), args)

    def _args(self, args: Sequence[libcst.Arg]) -> list[libcst.Arg] | None:
        names = _names(arg.value for arg in args if _is_positional(arg))
        expr = _expr_dict([arg for arg in args if not _is_positional(arg)])
        if names is None or expr is None or not (names or expr.elements):
            return None
        if not names:
            return [libcst.Arg(_unwrap(expr))]
        select = [libcst.Arg(name) for name in names]
        if expr.elements:
            select.append(_kwarg("expr", expr))
        return select


@frozen
class JoinRule(CstRule[libcst.Call, libcst.BaseExpression]):
    """`t.join(r, keys, how=...)` and `t.<how>_join(r, keys)` → `t @ it.<How>Join(r, keys=[...])`.

    Only equality keys by name; predicate joins and other options stay.
    """

    def apply(self, node: libcst.Call) -> libcst.BaseExpression | None:
        how = self._how(node)
        if how is None or (table := _receiver_of(node)) is None:
            return None
        args = [arg for arg in node.args if not _is_keyword(arg, "how")]
        if len(args) != 2 or args[0].keyword or args[0].star:  # right table and keys
            return None
        if args[1].keyword and args[1].keyword.value != "predicates":
            return None
        keys = _key_list(args[1].value)
        if keys is None:
            return None
        return _flow(table, _it(how), [libcst.Arg(args[0].value), _kwarg("keys", keys)])

    def _how(self, node: libcst.Call) -> str | None:
        method = _method_name(node)
        if method is not None and method.endswith("_join"):
            return _JOIN_HOW.get(method.removesuffix("_join"))
        if method != "join":
            return None
        how = next((arg.value for arg in node.args if _is_keyword(arg, "how")), None)
        if how is None:
            return _JOIN_HOW["inner"]
        if isinstance(how, libcst.SimpleString):
            return _JOIN_HOW.get(str(how.evaluated_value))
        return None


@frozen
class CrossJoinRule(CstRule[libcst.Call, libcst.BaseExpression]):
    """`t.cross_join(r)` → `t @ it.InnerJoin(r, keys=[])`."""

    def apply(self, node: libcst.Call) -> libcst.BaseExpression | None:
        if (table := _receiver(node, "cross_join")) is None:
            return None
        if not node.args or not all(_is_positional(arg) for arg in node.args):
            return None
        rights = [libcst.Arg(arg.value) for arg in node.args]
        return _flow(
            table, _it("InnerJoin"), [*rights, _kwarg("keys", libcst.List([]))]
        )


@frozen
class AggregateRule(CstRule[libcst.Call, libcst.BaseExpression]):
    """`t.group_by(*k).aggregate(n=x)` → `t @ it.Aggregate(by=[*k], expr={"n": x})`."""

    def apply(self, node: libcst.Call) -> libcst.BaseExpression | None:
        grouped = _receiver(node, "aggregate")
        if not isinstance(grouped, libcst.Call):
            return None
        if (table := _receiver(grouped, "group_by")) is None:
            return None
        keys = _group_keys(grouped.args)
        expr = _expr_dict(node.args)
        if keys is None or expr is None or not expr.elements:
            return None
        return _flow(
            table, _it("Aggregate"), [_kwarg("by", keys), _kwarg("expr", expr)]
        )


TABLE_RULES: tuple[TableRule, ...] = (
    AggregateRule(),
    FilterRule(),
    SelectRule(),
    JoinRule(),
    CrossJoinRule(),
)


@define(slots=False)
class TableTransformer(libcst.CSTTransformer):
    """Apply `rules` to every call, bottom-up, so chains become flat flows."""

    rules: Sequence[TableRule] = TABLE_RULES
    _changed: bool = field(default=False, init=False)

    @override
    def visit_Module(self, node: libcst.Module) -> bool:
        self._changed = False
        return True

    @override
    def leave_Call(
        self, original_node: libcst.Call, updated_node: libcst.Call
    ) -> libcst.BaseExpression:
        for rule in self.rules:
            if (node := updated_node @ rule) is not None:
                self._changed = True
                # Keep the call's own parentheses, e.g. around a multi-line chain.
                return node.with_changes(lpar=updated_node.lpar, rpar=updated_node.rpar)
        return updated_node

    @override
    def leave_Attribute(
        self, original_node: libcst.Attribute, updated_node: libcst.Attribute
    ) -> libcst.Attribute:
        return updated_node.with_changes(value=_grouped(updated_node.value))

    @override
    def leave_Subscript(
        self, original_node: libcst.Subscript, updated_node: libcst.Subscript
    ) -> libcst.Subscript:
        return updated_node.with_changes(value=_grouped(updated_node.value))

    @override
    def leave_UnaryOperation(
        self, original_node: libcst.UnaryOperation, updated_node: libcst.UnaryOperation
    ) -> libcst.UnaryOperation:
        return updated_node.with_changes(expression=_grouped(updated_node.expression))

    @override
    def leave_BinaryOperation(
        self,
        original_node: libcst.BinaryOperation,
        updated_node: libcst.BinaryOperation,
    ) -> libcst.BinaryOperation:
        if not isinstance(updated_node.operator, _TIGHT_OPERATORS):
            return updated_node
        left = updated_node.left
        if isinstance(updated_node.operator, libcst.Power):
            left = _grouped(left)
        return updated_node.with_changes(left=left, right=_grouped(updated_node.right))

    @override
    def leave_Module(
        self, original_node: libcst.Module, updated_node: libcst.Module
    ) -> libcst.Module:
        if not self._changed:
            return updated_node
        imports = AddImportsVisitor(CodemodContext(), [ImportItem("ibis_typing", "it")])
        return imports.transform_module(updated_node)


def _receiver(node: libcst.Call, method: str) -> libcst.BaseExpression | None:
    """Return the table `node` calls `method` on, unless a string (`str.join`)."""
    if _method_name(node) != method:
        return None
    return _receiver_of(node)


def _receiver_of(node: libcst.Call) -> libcst.BaseExpression | None:
    if not isinstance(node.func, libcst.Attribute):
        return None
    table = node.func.value
    # `it.deferred.filter(...)` is already a flow step, not a table.
    if isinstance(table, _STRINGS) or _is_deferred(table):
        return None
    # A flow earlier in the chain was parenthesized by `leave_Attribute`;
    # `@` groups left to right, so `(t @ A) @ B` is `t @ A @ B`.
    # Parentheses around a multi-line flow are the source's and must stay.
    if _is_flow(table) and table.lpar and _single_line(table):
        return table.with_changes(lpar=[], rpar=[])
    return table


def _single_line(flow: libcst.BaseExpression) -> bool:
    """Whether no `@` in the flow's left spine is followed or preceded by a newline."""
    while isinstance(flow, libcst.BinaryOperation) and _is_flow(flow):
        operator = flow.operator
        assert isinstance(operator, libcst.MatrixMultiply)
        spaces = (operator.whitespace_before, operator.whitespace_after)
        if not all(isinstance(space, libcst.SimpleWhitespace) for space in spaces):
            return False
        flow = flow.left
    return True


def _method_name(node: libcst.Call) -> str | None:
    if isinstance(node.func, libcst.Attribute):
        return node.func.attr.value
    return None


def _flow(
    table: libcst.BaseExpression, op: libcst.BaseExpression, args: Sequence[libcst.Arg]
) -> libcst.BaseExpression:
    call = libcst.Call(
        func=op,
        args=[arg.with_changes(comma=libcst.MaybeSentinel.DEFAULT) for arg in args],
    )
    return table @ MatMul(call)


def _it(*attrs: str) -> libcst.BaseExpression:
    node: libcst.BaseExpression = libcst.Name("it")
    for attr in attrs:
        node = libcst.Attribute(value=node, attr=libcst.Name(attr))
    return node


def _kwarg(keyword: str, value: libcst.BaseExpression) -> libcst.Arg:
    no_space = libcst.SimpleWhitespace("")
    return libcst.Arg(
        value,
        keyword=libcst.Name(keyword),
        equal=libcst.AssignEqual(whitespace_before=no_space, whitespace_after=no_space),
    )


def _is_positional(arg: libcst.Arg) -> bool:
    return arg.keyword is None and not arg.star


def _is_keyword(arg: libcst.Arg, keyword: str) -> bool:
    return arg.keyword is not None and arg.keyword.value == keyword


def _names(
    values: Iterable[libcst.BaseExpression],
) -> list[libcst.BaseExpression] | None:
    """Column names (`"a"`, `cols.a`, `this[cols.a]` → `cols.a`), or None."""
    names = [_name(value) for value in values]
    if any(name is None for name in names):
        return None
    return [name for name in names if name is not None]


def _name(value: libcst.BaseExpression) -> libcst.BaseExpression | None:
    if isinstance(value, (libcst.SimpleString, libcst.Name, libcst.Attribute)):
        return value
    match value:
        case libcst.Subscript(
            value=libcst.Name("this"),
            slice=[libcst.SubscriptElement(slice=libcst.Index(value=inner))],
        ):
            return _name(inner)
        case _:
            return None


def _key_list(value: libcst.BaseExpression) -> libcst.List | None:
    """Join keys as a list of names, from one name or a list/tuple of them."""
    if isinstance(value, (libcst.List, libcst.Tuple)):
        if any(not isinstance(e, libcst.Element) for e in value.elements):
            return None
        names = _names([e.value for e in value.elements])
    else:
        names = _names([value])
    if names is None:
        return None
    return libcst.List([libcst.Element(name) for name in names])


def _group_keys(args: Sequence[libcst.Arg]) -> libcst.List | None:
    if not args or not all(_is_positional(arg) for arg in args):
        return None
    if len(args) == 1:
        return _key_list(args[0].value)
    names = _names([arg.value for arg in args])
    if names is None:
        return None
    return libcst.List([libcst.Element(name) for name in names])


def _expr_dict(args: Sequence[libcst.Arg]) -> libcst.Dict | None:
    """`{"name": value, **mapping}` from keyword and `**` arguments, or None."""
    elements: list[libcst.BaseDictElement] = []
    for arg in args:
        if arg.keyword is not None:
            key = libcst.SimpleString(f'"{arg.keyword.value}"')
            elements.append(libcst.DictElement(key, arg.value))
        elif arg.star == "**":
            elements.append(libcst.StarredDictElement(arg.value))
        else:
            return None
    return libcst.Dict(elements)


def _is_deferred(node: libcst.BaseExpression) -> bool:
    match node:
        case libcst.Name("deferred") | libcst.Attribute(attr=libcst.Name("deferred")):
            return True
        case _:
            return False


def _unwrap(expr: libcst.Dict) -> libcst.BaseExpression:
    """Reduce `{**mapping}` to `mapping`."""
    match expr.elements:
        case [libcst.StarredDictElement(value=mapping)]:
            return mapping
        case _:
            return expr


def _is_flow(node: libcst.BaseExpression) -> bool:
    return isinstance(node, libcst.BinaryOperation) and isinstance(
        node.operator, libcst.MatrixMultiply
    )


def _grouped(node: libcst.BaseExpression) -> libcst.BaseExpression:
    """Parenthesize a flow the rules built where it is an operand of a tighter operator.

    A flow from the source is already parenthesized there, or it would not parse
    as one; this keeps `t.filter(p).columns` from becoming `t @ F(p).columns`.
    """
    if _is_flow(node) and not node.lpar:
        return node @ Parenthesize()
    return node
