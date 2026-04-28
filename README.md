# df-pipeline

Declarative DataFrame transformation library for Python ETL pipelines.

Define your data transformations in YAML — renames, casts, filters, deduplication, column arithmetic — and apply them with a single function call. No boilerplate, no repeated logic across scripts.

```python
import yaml
from df_pipeline import TransformConfig, apply_base_transform

config = TransformConfig.model_validate(yaml.safe_load(open("config.yaml"))["transform"]["data"])
df_out = apply_base_transform(df_raw, config)
```

---

## Installation

```bash
pip install pandas pydantic pyyaml
# then clone this repo and install locally
pip install -e .
```

**Requirements:** Python 3.10+, pandas >= 2.0, pydantic >= 2.0, pyyaml >= 6.0

---

## Quickstart

### 1. Write a config file

```yaml
# config.yaml
transform:
  data:
    renames:
      flow_rate: flow_rate_m3h
      end_data: end_date

    assigns:
      data_source: "my_pipeline"

    column_transforms:
      - op: to_datetime
        col: start_date
        dest: start_date

      - op: date_diff
        col: end_date
        other_col: start_date
        dest: duration_days
        params:
          unit: days

    column_filters:
      - col: group
        op: eq
        value: "A"
      - col: flow_rate_m3h
        op: gt
        value: 13.0

    drop_duplicates:
      - node_id
      - start_date

    select:
      - node_id
      - group
      - flow_rate_m3h
      - duration_days

    index: node_id
```

### 2. Apply in Python

```python
import yaml
import pandas as pd
from df_pipeline import TransformConfig, apply_base_transform

df_raw = pd.read_csv("data.csv")
params = yaml.safe_load(open("config.yaml"))

config = TransformConfig.model_validate(params["transform"]["data"])
df_out = apply_base_transform(df_raw, config)
```

Or construct entirely in Python without YAML:

```python
from df_pipeline import TransformConfig, ColumnFilter, ColumnTransform, apply_base_transform

config = TransformConfig(
    renames={"flow_rate": "flow_rate_m3h"},
    column_transforms=[
        ColumnTransform(col="end_date", other_col="start_date",
                        op="date_diff", dest="duration_days",
                        params={"unit": "days"}),
    ],
    column_filters=[
        ColumnFilter(col="group", op="eq", value="A"),
    ],
    index="node_id",
)
df_out = apply_base_transform(df_raw, config)
```

---

## Transformation pipeline

Steps execute in this fixed order:

| Step | Field | Description |
|------|-------|-------------|
| 1 | `renames` | Rename columns |
| 2 | `assigns` | Add or overwrite columns with scalar values |
| 3 | `column_transforms` | Cast, compute, or convert columns |
| 4 | `column_filters` | Filter rows (combined with AND) |
| 5 | `drop_duplicates` | Drop duplicate rows |
| 6 | `select` | Keep only specified columns |
| 7 | `index` | Set DataFrame index |

All steps are optional. Omitted steps are skipped.

---

## Column transforms

Built-in ops:

| Op | Description | Required params |
|----|-------------|-----------------|
| `to_numeric` | Cast to numeric | `errors` (optional, default `"raise"`) |
| `to_datetime` | Cast to datetime | any `pd.to_datetime` kwarg |
| `tz_convert` | Timezone conversion | `tz` (required) |
| `date_diff` | Signed difference between two datetime columns, returns float | `unit`: `"days"`, `"hours"`, `"minutes"`, `"seconds"` (default) |

```yaml
column_transforms:
  - op: to_numeric
    col: pressure
    dest: pressure
    params:
      errors: coerce

  - op: date_diff
    col: end_date
    other_col: start_date
    dest: elapsed_days
    params:
      unit: days
```

If `dest` is omitted, the result overwrites `col`.

### Registering custom ops

```python
from df_pipeline.registry import TransformSpec, register_transform

def _m3h_to_ls(s1, s2=None, **kwargs):
    return s1 / 3.6

# register before any TransformConfig is instantiated
register_transform("m3h_to_ls", TransformSpec(fn=_m3h_to_ls))
```

Then use it in YAML or Python exactly like a built-in op:

```yaml
- op: m3h_to_ls
  col: flow_rate_m3h
  dest: flow_rate_ls
```

---

## Row filters

Filters are combined with logical AND. Supported operators:

| Op | Meaning |
|----|---------|
| `eq`, `ne` | Equal / not equal |
| `gt`, `ge` | Greater than / greater or equal |
| `lt`, `le` | Less than / less or equal |
| `startswith`, `endswith`, `contains` | String operations |

```yaml
column_filters:
  - col: well_id
    op: startswith
    value: "PW"
  - col: flow_rate
    op: gt
    value: 500.0
  # compare two columns directly
  - col: measured_flow
    op: gt
    other_col: expected_flow
```

Custom filter operators can be added via `OP_MAPPERS`:

```python
from df_pipeline.registry import OP_MAPPERS

OP_MAPPERS["between"] = lambda s, x: s.between(x[0], x[1])
```

---

## CLI runner pattern

`df_pipeline` includes CLI helpers for building consistent runner scripts.
See [`examples/example_etl.py`](examples/example_etl.py) for a full working example.

```python
import logging, sys
from df_pipeline.cli import default_parser, log_runner

logger = logging.getLogger(__name__)

@log_runner("my_etl", logger)
def main(*, config_filename, dry_run=False, run_start_dttm=None):
    ...

if __name__ == "__main__":
    args = default_parser("My ETL pipeline").parse_args()

    level = logging.DEBUG if args.debug else logging.INFO if args.verbose else logging.WARNING
    logging.basicConfig(level=level, format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s")

    main(config_filename=args.config or "config.yaml", dry_run=args.dry_run)
```

`default_parser` provides: `config` (positional, optional), `--verbose`/`--silent`, `--debug`/`--no-debug`, `--dry-run`.

`log_runner` injects `run_start_dttm` (a `pd.Timestamp`) and logs elapsed time automatically.

---

## Project structure

```
src/df_pipeline/
├── __init__.py          # public API
├── registry.py          # TransformSpec, OP_MAPPERS, COLUMN_TRANSFORM_REGISTRY
├── schema.py            # Pydantic models: TransformConfig, ColumnFilter, ColumnTransform
├── filters.py           # build_mask
├── column_transforms.py # apply_column_transforms
├── transforms.py        # apply_base_transform (pipeline orchestrator)
└── cli.py               # log_runner, default_parser

examples/
├── example_etl.py       # full runner example with logging and CLI
├── data/                # sample CSV
└── config/              # sample YAML config
```

---

## Running the tests

```bash
PYTHONPATH=src:. pytest tests/ -v
```

---

## License

MIT
