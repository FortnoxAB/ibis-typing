from __future__ import annotations

from ibis_typing.refactor.ibis_cst import IbisFuncToMethodRule, IbisTransformer


class IbisApiRule(IbisFuncToMethodRule):
    func_module = "ibis"
    method_module = "it"


class IbisTimeRule(IbisFuncToMethodRule):
    func_module = "ibis_time"


class IbisOpsRule(IbisFuncToMethodRule):
    func_module = "ibis_ops"


MIGRATIONS = {
    "api": IbisTransformer(
        [
            IbisApiRule("desc", "Desc"),
            IbisApiRule("ifelse", "IfElse"),
            IbisApiRule("cases", "Cases", left_kw="else_"),
            IbisApiRule("coalesce", "FillNull"),
            IbisApiRule("greatest", "Greatest"),
            IbisApiRule("least", "Least"),
            IbisApiRule("and_", "And"),
            IbisApiRule("or_", "Or"),
        ],
        import_line="from ibis_typing import it",
    ),
    "ibis_ops": IbisTransformer(
        [
            IbisOpsRule("column_checksum", "ColumnChecksum"),
            IbisOpsRule("parse_json", "JsonParse"),
            IbisOpsRule("json_format", "JsonFormat"),
            IbisOpsRule("uuid_from_int", "IntToUUID"),
            IbisOpsRule("luhn_check", "LuhnCheck"),
        ],
        import_from="ibis_typing.ibis_ops",
    ),
    "ibis_time": IbisTransformer(
        [
            IbisTimeRule("truncate_month", "StartOfMonth"),
            IbisTimeRule("diff_months", "MonthsSince"),
            IbisTimeRule("diff_days", "DaysSince"),
            IbisTimeRule("add_months", "AddMonths"),
            IbisTimeRule("add_days", "AddDays"),
        ],
        import_from="ibis_typing.ibis_time",
    ),
}
