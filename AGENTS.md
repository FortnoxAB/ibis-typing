# AGENTS.md — ibis-typing

Developer and agent reference for the `ibis-typing` repository.
A Python library (and pytest plugin) for typed [Ibis](https://ibis-project.org/) dataframe expressions.

---

## Tech Stack

| Layer                | Technology                                     |
|----------------------|------------------------------------------------|
| Language             | Python ≥ 3.12                                  |
| Package manager      | `uv`                                           |
| Build backend        | `hatchling`                                    |
| Linting / formatting | `ruff`                                         |
| Type checking        | `pyrefly`                                      |
| Dependency auditing  | `deptry`                                       |
| Testing              | `pytest` + `hypothesis`                        |
| Coverage             | `coverage.py` (≥ 90% branch coverage enforced) |
| Core dependency      | `ibis-framework[duckdb,trino]`                 |

---

## Build & Install

```bash
make deps        # uv sync --all-extras (installs everything)
make clean       # Remove .venv and reinstall from scratch
make             # Full CI pipeline: deps → lint → test → coverage
```

---

## Lint & Format

```bash
make lint        # ruff check + ruff format --check + deptry + pyright (all checks)
make format      # uv run ruff format           (auto-fix formatting)
make fix         # uv run ruff check --fix      (auto-fix lint issues)
make fix_unsafe  # uv run ruff check --fix --unsafe-fixes
make add_noqa    # uv run ruff check --add-noqa (suppress remaining issues)
```

Individual checks:

```bash
uv run ruff check          # lint only
uv run ruff format --check # format check only
uv run deptry .            # dependency audit
uv run pyright             # type checking
```

---

## Testing

Tests are segmented by backend using pytest markers.

### Run all tests (full CI suite)

```bash
make test
```

### Run a specific category

```bash
# Unit tests only (no database backend required)
uv run coverage run -m pytest --exitfirst --durations=10 -m "not ibis"

# DuckDB integration tests
TEST_IBIS_BACKEND=duck uv run coverage run -m pytest --exitfirst --durations=10 -m "duck"

# Trino integration tests (uses testcontainers)
TEST_IBIS_BACKEND=trino uv run coverage run -m pytest --exitfirst --durations=10 -m "trino"
```

### Run a single test file

```bash
uv run pytest tests/test_ibis_utils.py
uv run pytest ibis_typing/hypothesis/tests/test_hypothesis_transforms.py
```

### Run a single test case

```bash
uv run pytest tests/test_ibis_utils.py::test_select_cols
uv run pytest -k "test_sums_transactions_by_month"
```

### Doctests

Every `.py` file with `>>>` examples in docstrings is automatically tested
(`--doctest-modules` is in `addopts`). Run doctests for a single module:

```bash
uv run pytest --doctest-modules ibis_typing/utils.py
```

### Pytest configuration (from `pyproject.toml`)

```toml
[tool.pytest.ini_options]
addopts = "--doctest-modules --strict-markers"
doctest_optionflags = ["ELLIPSIS"]   # '...' matches any output in doctests
markers = ["ibis", "duck", "trino"]
```

Backend markers are **applied automatically** by the pytest plugin based on
which fixtures a test uses — no manual `@pytest.mark.*` needed in most cases.

---

## Code Style

### Formatting rules (ruff)

- Line length: **88** characters
- Quotes: **double** (`"`)
- Indent: **spaces**
- Docstring code blocks are also formatted (`docstring-code-format = true`)

### Enabled rule sets (ruff lint)

`F`, `FA`, `TID`, `COM`, `C4`, `PTH`, `I` (isort), `PLE`, `PLR`, `PLW`,
`E`, `W`, `UP` (pyupgrade), `FURB`, `RUF`

Notable ignores: `E501` (line length), `COM812` (trailing comma), `PLR2004`
(magic values), `TID252` (relative imports from parent).

### Suppressing known violations

Use inline `# noqa: <code>` comments sparingly:

```python
def aggregate(...):  # noqa: PLR0913  # Too many arguments
```

---

## Imports

1. **Always add `from __future__ import annotations`** as the first line of
   every module. This enables deferred annotation evaluation (PEP 563).
2. Use **absolute imports** from the package root by default.
3. Use **relative imports** only within `ibis_typing/` itself:
   ```python
   from .ibis_adapter import IbisSchema, IbisTable
   from . import ibis_types as it
   ```
4. **Define `__all__`** in every public module.
5. Use `TYPE_CHECKING` guards for imports that are only needed by the type
   checker, not at runtime:
   ```python
   from typing import TYPE_CHECKING
   if TYPE_CHECKING:
       from .ibis_adapter import IbisSchema
   ```
6. Local imports inside function bodies are acceptable to break circular
   import cycles — add a comment explaining the reason.

---

## Types & Annotations

This project targets **Python 3.12+** and uses its newest syntax everywhere.

### Type aliases — use the `type` statement

```python
type Int64 = int | IntegerType | None
type Array[T] = Sequence[T] | ArrayType[T] | None
type TableMap[S: IbisSchema] = MutableMapping[type[S], IbisTable[S]]
```

### Generic classes — use PEP 695 syntax

```python
class IbisTable[S: IbisSchema]: ...


def fetch_table[T: IbisSchema](self, table: IbisTable[T]) -> Iterable[T]: ...
```

### IbisSchema field annotations

Always annotate fields with `it.*` type aliases, **not** Python builtins or
raw ibis types:

```python
from ibis_typing import ibis_types as it


class MySchema(IbisSchema):
    id: it.Int64
    name: it.String
    tags: it.Array[it.String]
```

### Use `cast()` when the type checker cannot infer

```python
from typing import cast

this = cast(ibis.Table, ibis._)
```

### `attrs.frozen` instead of `dataclass`

Use `@frozen` from `attrs` (immutable, `__slots__`-based) as the default
decorator for all new data-holding classes:

```python
from attrs import frozen


@frozen
class MyOp:
    col: Value
    scale: int = 1
```

---

## Naming Conventions

| Entity              | Convention           | Example                           |
|---------------------|----------------------|-----------------------------------|
| Files / modules     | `snake_case`         | `ibis_adapter.py`                 |
| Classes             | `PascalCase`         | `IbisTable`, `ColumnChecksum`     |
| Functions / methods | `snake_case`         | `fetch_table()`, `strategy_for()` |
| Variables / params  | `snake_case`         | `group_by`, `table_schema`        |
| Type aliases        | `PascalCase`         | `Int64`, `TableMap`               |
| Private helpers     | Leading `_`          | `_chained`, `_get_cols()`         |
| Test files          | `test_<module>.py`   | `test_ibis_utils.py`              |
| Test functions      | `test_<description>` | `test_select_cols`                |

---

## Error Handling

- Use **assertions** for internal invariants: `assert table`, `assert target`
- Raise **`ValueError`** for caller-visible contract violations
- Raise **`TypeError`** for type contract violations
- Raise **`LookupError`** for registry misses
- No custom exception hierarchy — use standard Python exceptions
- Error messages should be descriptive and include relevant context:
  ```python
  raise ValueError(f"There are unused input schemas: {unused}")
  raise LookupError(f"Method {method.__qualname__} not found.")
  ```

---

## Architecture Patterns

### Infix `@` operator for table transforms

All `TableMethod` subclasses are applied with `@` (overloads `__rmatmul__`):

```python
table @ Select(cols.id) @ Aggregate(by=[cols.id])
```

### `deferred` for native ibis method chaining after extension methods

```python
from ibis_typing import it

table @ MyTransform(...) @ it.deferred.filter(cond).order_by(col)
```

### Expression / Evaluator pattern

Business logic is expressed as `Expression` subclasses with typed inputs and
outputs. The `Evaluator` wires them together via dependency injection.

---

## Testing Patterns

### Arrange / Act / Assert

```python
def test_select_cols(fetch_table):
    rows = [SimpleSchema(id=0, value=2), SimpleSchema(id=1, value=3)]
    expected = [SelectCols(id=0), SelectCols(id=1)]
    table = SimpleSchema.of_rows(rows).table @ Select(SimpleSchema.cols.id)
    actual = fetch_table(SelectCols.of(table))
    assert actual == expected
```

### Hypothesis / property-based tests

```python
from ibis_typing.hypothesis.strategies import strategy_for
from hypothesis import given
import hypothesis.strategies as st


@given(st.lists(strategy_for(Transaction), min_size=1))
def test_sums_by_month(evaluate_table, transactions):
    expected = [MonthlyAmounts(...) for ...]
    actual, expected = evaluate_table(MonthlyAmounts, transactions + expected)
    assert actual == expected
```

### Doctests

Every public function should have a doctest where practical. Use `...` freely
(ELLIPSIS is enabled):

```python
def short_hash(obj, length: int = 8) -> str:
    """Return a short hash.

    >>> short_hash("hello")
    'aaf4c61d'
    """
```

### Coverage

Branch coverage is enforced at **90%** minimum. New code must include tests.
