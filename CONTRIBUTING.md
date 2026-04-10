# Contributing to ibis-typing

Thank you for your interest in contributing! This document covers how to set up a development environment, run tests, and submit changes.

## Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) (recommended) or pip

## Setting up the development environment

```bash
git clone https://github.com/FortnoxAB/ibis-typing
cd ibis-typing
uv sync --all-extras
uv run python -m ibis_typing.type_patch
```

The last command patches your installed `ibis` package with typed overloads. It needs to be re-run whenever `ibis` is upgraded.

## Running tests

Tests are split by backend. Most development workflows only need the first two:

```bash
# Lint (ruff, type checker, dependency checker)
make lint

# Unit tests (no backend required)
make test_unittests

# DuckDB integration tests
make test_duck

# Trino integration tests (requires Docker)
make test_trino
```

Run the full suite including coverage:

```bash
make test
```

Coverage must remain at or above 90%.

## Code quality

Before submitting a PR, make sure lint passes:

```bash
make lint
```

To auto-fix formatting and safe linting issues:

```bash
make format   # ruff format
make fix      # ruff check --fix
```

The project uses:
- **ruff** — linting and formatting
- **ty** — type checking
- **deptry** — dependency hygiene

## Making changes

1. Fork the repository and create a branch from `main`.
2. Write tests for new behaviour.
3. Run `make lint` and `make test_unittests test_duck` to verify.
4. Open a pull request with a clear description of what changed and why.

There is no formal CLA — by submitting a PR you agree that your contribution will be licensed under [MIT](LICENSE).

## Reporting issues

Please open a GitHub issue with:
- A minimal reproducible example
- Your Python version (`python --version`)
- Your ibis version (`python -c "import ibis; print(ibis.__version__)"`)
- The full traceback if applicable
