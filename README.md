# ibis-typing

[![PyPI](
https://img.shields.io/pypi/v/ibis-typing)](
https://pypi.org/project/ibis-typing/)
[![License: MIT](
https://img.shields.io/badge/License-MIT-yellow.svg)](
LICENSE)
[![Python](
https://img.shields.io/pypi/pyversions/ibis-typing)](
https://pypi.org/project/ibis-typing/)
[![CI](
https://github.com/FortnoxAB/ibis-typing/actions/workflows/ci.yml/badge.svg)](
https://github.com/FortnoxAB/ibis-typing/actions/workflows/ci.yml)
[![Coverage](
https://codecov.io/gh/FortnoxAB/ibis-typing/branch/main/graph/badge.svg)](
https://codecov.io/gh/FortnoxAB/ibis-typing)
[![Ruff](
https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](
https://github.com/astral-sh/ruff)
[![ty](
https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ty/main/assets/badge/v0.json)](
https://github.com/astral-sh/ty)
[![uv](
https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](
https://github.com/astral-sh/uv)

A typed framework for writing [Ibis](https://ibis-project.org/) dataframe expressions — with full IDE support, static
analysis, and property-based testing.

[Ibis](https://ibis-project.org/) is a portable Python dataframe library (DSL) that runs on DuckDB, Polars, Trino,
BigQuery, and more. **ibis-typing** layers a type-safe schema system on top of it, so your transforms carry type
information end-to-end.

## Installation

```bash
pip install ibis-typing
```

```bash
uv add ibis-typing
```

After installation, run the type-patch step once to inject typed overloads into your installed `ibis` package:

```bash
python -m ibis_typing.type_patch
```

## Quick start

### 1. Define input schemas

```python
from attrs import frozen

from ibis_typing import IbisSchema, it


@frozen
class Transaction(IbisSchema):
    date: it.Date = None
    amount: it.Float64 = None
    category: it.String = None
```

### 2. Define a typed expression

```python
from attrs import frozen
from collections.abc import Sequence
from ibis_typing import Expression, IbisTable, this, it
from ibis_typing.ibis_extension_method import TableMethod, ValueMethod
from ibis import Table, ir, literal


@frozen
class MonthlyAmounts(Expression):
    month: it.Date = None
    amount: it.Float64 = None

    @classmethod
    def from_expression(cls, inputs: IbisTable[Transaction]):
        cols = inputs.cols
        table = (
            inputs.table
            @ AggregateByMonth(cols.date, sums=[cols.amount])
            @ it.deferred.filter(this[cols.amount] != literal(0))
        )
        return cls.of(table)


@frozen
class AggregateByMonth(TableMethod):
    date: it.Date
    sums: Sequence[it.Float64]

    def apply(self, table: Table) -> Table:
        return (
            table
            @ it.Select(expr={"month": this[self.date] @ StartOfMonth()})
            @ it.Aggregate(by=["month"], sum=self.sums)
        )


@frozen
class StartOfMonth(ValueMethod[ir.DateValue, ir.DateValue]):
    def apply(self, value: ir.DateValue):
        return value @ it.defer(ir.DateValue).truncate("M")
```

> **Tip:** `IbisSchema` classes for your `Expression` outputs can be generated automatically using
`ibis_typing.schema_writer`. The code is backend-agnostic — schemas are derived from abstract Ibis table schemas, so no
> live backend is required.

### 3. Evaluate against a backend

```python
from datetime import date

from ibis_typing import IbisConnection, evaluator
from ibis_typing.table_store import ParquetTableStore

conn = IbisConnection()  # defaults to in-memory DuckDB
transactions = Transaction.of_rows(  # give test data via IbisSchema rows.
    [Transaction(date=date(2024, 1, 15), amount=100.0, category="A")]
)
monthly_amounts = evaluator.from_expression(MonthlyAmounts, transactions)
results: list[MonthlyAmounts] = list(conn.fetch_table(monthly_amounts))

# Write and read parquet files locally, stored by schema name.
from pathlib import Path

store = ParquetTableStore(Path("/tmp/table_store"))
store.write_table(transactions)
table = store(Transaction)
rows: list[Transaction] = list(conn.fetch_table(table))
```

### 4. Test with Hypothesis

pytest fixtures are registered automatically — no `conftest.py` needed.

```python
from hypothesis import given, strategies as st

from ibis_typing import utils
from ibis_typing.hypothesis import strategy_for


@given(transactions=st.lists(strategy_for(Transaction), min_size=1))
def test_monthly_amounts(evaluate_table, transactions):
    reference_output = utils.group_by(transactions, key=lambda t: t.date.replace(day=1))
    monthly_amounts = [
        MonthlyAmounts(month=month, amount=sum(t.amount for t in month_transactions))
        for month, month_transactions in reference_output.items()
    ]

    # Get evaluated expression rows together with expected, both as sorted lists
    actual, expected = evaluate_table(MonthlyAmounts, [*transactions, *monthly_amounts])

    assert actual == expected
```

## Core concepts

```mermaid
graph TD
    IbisSchema -->|describes| IbisTable
    IbisTable -->|In| Expression
    Expression -->|Out| IbisTable
    TableProvider -->|provides tables to| Expression
    IbisConnection -->|fetches typed rows from| IbisTable
    ChecksumBuckets -->|incremental inputs to| IncrementalExpression
    IncrementalExpression -->|is a| Expression
    BucketedInputsExpression -->|is a| IncrementalExpression
    RevertibleTableExpression -->|can revert| Expression
```

| Class                       | Purpose                                                                      |
|-----------------------------|------------------------------------------------------------------------------|
| `IbisSchema`                | Base class for typed table schemas (attrs frozen dataclass)                  |
| `IbisTable[S]`              | Generic typed wrapper around `ibis.Table`                                    |
| `Expression`                | Abstract base for typed ibis transforms                                      |
| `TableMethod`               | Extension method on `ibis.Table` returning another Table                     |
| `ValueMethod`               | Extension method on `ibis.Value` returning another Value                     |
| `Deferred`                  | `table @ it.deferred.distinct()` `value @ it.defer().notnull()`              |
| `IbisConnection`            | Typed backend wrapper: `fetch_table()`, `evaluate()`, `read/write_parquet()` |
| `BucketedInputsExpression`  | Expression that only re-runs for changed input buckets                       |
| `ChecksumBuckets`           | Checksum-based incremental input tracking                                    |
| `RevertibleTableExpression` | Transform that can undo itself back to the original schema                   |

## Type aliases

Declare schema fields using column-type aliases from `ibis_typing.it`:

```python
from ibis_typing import it

it.Int8, it.Int16, it.Int32, it.Int64
it.Float32, it.Float64
it.Boolean
it.String, it.Binary
it.Decimal
it.Date, it.Time, it.Timestamp
it.UUID, it.JSON
it.Array[it.Int64]
it.Map[it.String, it.Float64]
it.Struct[MyTypedDict]
```

## Table operations

Use the infix `@` operator for composable, typed table transforms via `TableMethod`. 
Standard Ibis Table methods are available via `it.deferred.distinct()`.
Ibis Value methods are available via e.g. `it.defer(type_=ir.Value).notnull()`.

```python
from ibis_typing import IbisSchema, IbisTable, this, it


@frozen
class InputSchema(IbisSchema):
    a: it.Float64 = None
    b: it.Float64 = None
    category: it.String = None
    amount: it.Float64 = None
    key: it.String = None


inputs: IbisTable[InputSchema] = ...
other_table: IbisTable = ...
cols = InputSchema.cols

table = (
    inputs.table
    @ it.Select(cols.a, cols.b, expr={"c": this[cols.a] + this[cols.b]})
    @ it.Aggregate(by=[cols.category], sum=[cols.amount])
    @ it.InnerJoin(other_table.table, keys=[cols.key])
    @ it.deferred.filter(this[cols.amount] != 0)
)
```

## Pytest fixtures

The following fixtures are auto-registered via the pytest plugin entry point (no `conftest.py` needed):

| Fixture           | Purpose                                                      |
|-------------------|--------------------------------------------------------------|
| `evaluate_table`  | Runs an `Expression`, returns `(actual, expected)` row lists |
| `fetch_table`     | Fetches rows from an `IbisTable`                             |
| `ibis_connection` | Provides a `IbisConnection` for relevant DB backends         |

## Extras

- **`ibis_typing.type_patch`** — patches installed ibis with typed `@overload` stubs for `ibis.ifelse`, `ibis.cases`,
  `ibis.coalesce`, etc.
- **`ibis_typing.schema_writer`** — code-gen: write `IbisSchema` `.py` files from `Expression` output schemas
- **`ibis_typing.plot`** — plots the dependency graph of an `Expression` using matplotlib/graphviz
- **`ibis_typing.custom`** — custom ibis operations: `DateAddMonth`, `DateAddDay`, `ColumnChecksum`, `JsonParse`,
  `JsonFormat`, `UUIDFromInt`, `LuhnCheck`

## Contributing

```bash
git clone https://github.com/FortnoxAB/ibis-typing
cd ibis-typing
make
```

Pull requests welcome. Please run `make` before submitting.

## License

[MIT](LICENSE)
