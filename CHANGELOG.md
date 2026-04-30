# Changelog

Notable changes to this project will be documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
Versioning follows [Semantic Versioning](https://semver.org/).

---

## [0.1.0] — 2026-04-28

Initial release.

### Added

**Core pipeline (`apply_base_transform`)** — fixed-order declarative pipeline:
renames → assigns → column transforms (see below) → row filters (see below) → drop duplicates → select → set index.

**Schema (`TransformConfig`, `ColumnFilter`, `ColumnTransform`)** — Pydantic v2 models
for programmatic or YAML-driven configuration. All fields optional; omitted steps are skipped.

**Column transform registry** — extensible registry (`COLUMN_TRANSFORM_REGISTRY`) with
built-in ops: `to_numeric`, `to_datetime`, `tz_convert`, `date_diff`.
Custom ops registered at runtime via `register_transform()`.

**Filter registry** — extensible `OP_MAPPERS` with numerical comparisons
(`eq`, `ne`, `gt`, `ge`, `lt`, `le`) and string ops (`startswith`, `endswith`, `contains`).
Supports both scalar and column-to-column comparisons.

**CLI helpers** — `log_runner` decorator (lifecycle logging + elapsed time) and
`default_parser` (pre-configured `argparse` with `--verbose`, `--debug`, `--dry-run`).

**Examples** — full runner script (`examples/example_etl.py`) with logging, CLI flags,
custom op registration, and annotated YAML config.

## [0.1.1] — 2026-04-30
Added multiindex capabilities for select and drop duplicates
Added sort operation