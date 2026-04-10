# Changelog

All notable changes to ibis-typing will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.0.0] - 2026-03-26

Initial open-source release under the MIT license.

### Added

- `IbisSchema` — base class for typed table schemas built on [attrs](https://www.attrs.org/) frozen dataclasses
- `IbisTable[S]` — generic typed wrapper around `ibis.Table`
- `Expression` — abstract base for typed Ibis transforms with `from_expression()` classmethod convention
- `IbisConnection` — typed backend wrapper with `fetch_table()`, `evaluate()`, `read_parquet()`, and `write_parquet()`
- `IncrementalExpression` — expression variant that re-runs only for changed input buckets via `ChecksumBuckets`
- `RevertibleTableExpression` — transform that can undo itself back to the original schema
- `ibis_typing.it` — column-type alias facade (`it.Int64`, `it.String`, `it.Date`, etc.)
- `ibis_typing.ibis_utils` — composable table operations via the `@` operator: `Select`, `Aggregate`, `InnerJoin`, `LeftJoin`
- `ibis_typing.hypothesis` — `strategy_for()` helper for property-based testing with [Hypothesis](https://hypothesis.works/)
- `ibis_typing.fixtures` — pytest plugin with auto-registered fixtures: `evaluate_table`, `fetch_table`, `ibis_connection`
- `ibis_typing.type_patch` — patches installed ibis with typed `@overload` stubs for `ibis.ifelse`, `ibis.cases`, `ibis.coalesce`, and more
- `ibis_typing.schema_writer` — code-gen utility to write `IbisSchema` `.py` files from `Expression` output schemas
- `ibis_typing.plot` — dependency graph visualisation using matplotlib/graphviz
- `ibis_typing.custom` — custom Ibis operations: `DateAddMonth`, `DateAddDay`, `ColumnChecksum`, `JsonParse`, `JsonFormat`, `UUIDFromInt`, `LuhnCheck`
- DuckDB and Trino backend support
- MIT license

[Unreleased]: https://github.com/FortnoxAB/ibis-typing/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/FortnoxAB/ibis-typing/releases/tag/v1.0.0
