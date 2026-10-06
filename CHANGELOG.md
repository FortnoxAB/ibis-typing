# Changelog

All notable changes to ibis-typing will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.2.0] - 2026-10-07

### Added

- `ibis_typing.time_series` — `TimeSeriesFeatureExtraction`, a `TableMethod` that adds trailing-window features per row
- `ibis_typing.time_series.features` — built-in features: `Sum`, `Mean`, `Min`, `Max`, `Count`, `NUnique`, `ApproxMedian`, `StandardDeviation`, `MeanAbsDiff`, `MedianFrequency`
- `PointFeature` and `SpectralFeature` — base classes for custom features, reducing `Points` or `Spectrum`
- `MedianFrequency` — computed on linearly detrended windows, so neither level nor trend dominates

## [1.1.0] - 2026-06-30

### Added

- `ibis_typing.ibis_api` — `value @ ValueMethod()` implementations of `ibis` API functions, exported through `ibis_typing.it`: `And`, `Or`, `Cases`, `Desc`, `FillNull`, `Greatest`, `IfElse`, `Least`
- `@`-calls can now be chained on `Deferred()` objects
- `ExpressionMethod` — chain `Expression` transforms with the `@` operator
- `ibis_typing.refactor` — CLI that rewrites `ibis.*` function calls to the `@` extension-method syntax (e.g. `ibis.ifelse(cond, l, r)` → `cond @ it.IfElse(l, r)`); requires the `dev` extra (`libcst`, `rope`)
- `ibis_typing.schemagen` — CLI for generating `IbisSchema` files
- `ibis_typing.dbt` — dbt integration framework: define models and snapshots as `Expression`s and compile them to dbt SQL, with `RevertibleTableExpression` support
- `ibis.literal(val)` return types are now annotated as `ibis.Value` for better type support

### Changed

- Internal data transforms now use the `value @ Method()` extension-method syntax
- Expression rewriter adds parentheses around more expression kinds
- `ruff` moved to the `dev` extra
- Pre-commit setup migrated to [prek](https://github.com/j178/prek)
- README updated with `TableMethod()`, `ValueMethod()` and `ParquetTableStore()` usage

## [1.0.1] - 2026-06-02

### Removed

- `ibis_typing.type_patch` no longer extends `ArrayValue`, `MapValue`, `StructValue` and `JSONValue`, so the type patcher is no longer required for these types. Nested types are an anti-pattern in most dataframes and perform poorly.

### Fixed

- README corrections

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

[Unreleased]: https://github.com/FortnoxAB/ibis-typing/compare/v1.2.0...HEAD
[1.2.0]: https://github.com/FortnoxAB/ibis-typing/compare/v1.1.0...v1.2.0
[1.1.0]: https://github.com/FortnoxAB/ibis-typing/compare/v1.0.1...v1.1.0
[1.0.1]: https://github.com/FortnoxAB/ibis-typing/compare/v1.0.0...v1.0.1
[1.0.0]: https://github.com/FortnoxAB/ibis-typing/releases/tag/v1.0.0
