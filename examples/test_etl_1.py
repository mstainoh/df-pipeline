"""
example_etl.py — minimal ETL runner using df_pipeline.

This script shows the canonical pattern for building a runner with this
library:

1. Register any custom transform ops before importing TransformConfig.
2. Parse CLI flags with default_parser().
3. Configure logging based on --verbose / --debug.
4. Read data and config from disk.
5. Apply the declarative transform pipeline.
6. Write output (skipped if --dry-run).

Running
-------
::

    # default (INFO logging)
    python examples/example_etl.py

    # with explicit config path
    python examples/example_etl.py examples/config/test_data_1.yaml

    # debug logging (shows every pipeline step)
    python examples/example_etl.py --debug

    # dry run (skips writing output)
    python examples/example_etl.py --dry-run

    # silent (WARNING+ only)
    python examples/example_etl.py --silent

Custom ops
----------
Register custom transform ops at the top of the script, before any
TransformConfig is instantiated. Pydantic validates op names at
construction time, so the registry must be populated first.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

# ---------------------------------------------------------------------------
# Register custom ops — MUST happen before TransformConfig is imported/used
# ---------------------------------------------------------------------------
from df_pipeline.registry import TransformSpec, register_transform

def _unit_convert(s1: pd.Series, s2=None, factor: float = 1.0, **kwargs) -> pd.Series:
    """Scale a numeric series by a constant factor.
    
    Typical use: flow unit conversion (m³/h → L/s uses factor=1/3.6).
    """
    return s1 * factor

def set_now(*args, **kwargs):
    """Return a Series of the current timestamp, aligned with the input series."""
    # We ignore the input series and just return the current time for all rows.
    return pd.Timestamp.now()

register_transform("unit_convert", TransformSpec(
    fn=_unit_convert,
    required_params=frozenset({"factor"}),
))

register_transform("now", TransformSpec(
    fn=set_now, requires_col=False
))


# ---------------------------------------------------------------------------
# df_pipeline imports (after registry is populated)
# ---------------------------------------------------------------------------
from df_pipeline.cli import default_parser, log_runner
from df_pipeline.schema import TransformConfig
from df_pipeline.transforms import apply_base_transform

# ---------------------------------------------------------------------------
# Module logger — inherits config from root logger set up in __main__
# ---------------------------------------------------------------------------
logger = logging.getLogger(__name__)

SCRIPT_NAME  = "example_etl"
DEFAULT_CONFIG = Path(__file__).parent / "config" / "test_data_1.yaml"
DEFAULT_DATA   = Path(__file__).parent / "data"   / "test_data_1.csv"


# ---------------------------------------------------------------------------
# IO helpers
# ---------------------------------------------------------------------------

def read_yaml(path: Path | str) -> dict:
    """Load a YAML file and return its contents as a dict.

    Raises
    ------
    AssertionError
        If the file is empty or contains only null.
    """
    path = Path(path)
    logger.debug("Reading YAML config: %s", path)
    with open(path, "rb") as fh:
        params = yaml.safe_load(fh)
    assert params is not None, f"Config file is empty: {path}"
    return params


def read_df(source: Path | str, **kwargs) -> pd.DataFrame:
    """Read a CSV or Parquet file into a DataFrame.

    The format is inferred from the file extension.

    Parameters
    ----------
    source : Path or str
        Path to the data file. Extension must be ``.csv`` or ``.parquet``.
    **kwargs
        Forwarded to :func:`pandas.read_csv` or :func:`pandas.read_parquet`.

    Raises
    ------
    ValueError
        If the file extension is not recognised.
    """
    path = Path(source)
    fmt  = path.suffix.lstrip(".")
    logger.debug("Reading %s file: %s", fmt.upper(), path)

    if fmt == "csv":
        df = pd.read_csv(path, **kwargs)
        df.columns = df.columns.str.strip()   # guard against whitespace in headers
        return df
    elif fmt == "parquet":
        return pd.read_parquet(path, **kwargs)
    else:
        raise ValueError(f'Unrecognised file format: "{fmt}". Expected csv or parquet.')


def transform(df: pd.DataFrame, params: dict[str, Any]) -> pd.DataFrame:
    """Validate a config dict and apply the declarative transform pipeline.

    Parameters
    ----------
    df : pd.DataFrame
        Raw input DataFrame.
    params : dict
        The ``transform.data`` block from the YAML config, already
        extracted by the caller.

    Returns
    -------
    pd.DataFrame
        Transformed DataFrame.
    """
    config = TransformConfig.model_validate(params)
    return apply_base_transform(df, config, logger=logger)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

@log_runner(SCRIPT_NAME, logger)
def main(
    *,
    config_filename: Path | str,
    dry_run: bool = False,
    run_start_dttm=None,          # injected by @log_runner
) -> pd.DataFrame:
    """
    End-to-end ETL: read → transform → (write).

    Parameters
    ----------
    config_filename : Path or str
        Path to the YAML config file.
    dry_run : bool
        If ``True``, skip writing outputs. The transformed DataFrame is
        still returned so callers can inspect it.
    run_start_dttm : pd.Timestamp
        Injected by :func:`~df_pipeline.cli.log_runner`. Can be used to
        stamp output tables with the run start time.
    """
    params = read_yaml(config_filename)

    data_path = Path(params["input"]["data"]["source"]).with_suffix(
        f".{params['input']['data']['reader']}"
    )
    logger.info("Input data: %s", data_path)

    df_raw = read_df(data_path)
    logger.info("Loaded %d rows × %d columns", *df_raw.shape)

    df_out = transform(df_raw, params["transform"]["data"])
    logger.info("Output: %d rows × %d columns", *df_out.shape)

    if dry_run:
        logger.info("Dry run — skipping write step.")
    else:
        # replace with your actual write logic (parquet, DB, etc.)
        out_path = Path("output") / f"{SCRIPT_NAME}_{run_start_dttm:%Y%m%d_%H%M%S}.csv"
        out_path.parent.mkdir(exist_ok=True)
        df_out.to_csv(out_path)
        logger.info("Output written to: %s", out_path)

    return df_out


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = default_parser(
        description="Example ETL runner — reads CSV, applies declarative transforms.",
    )
    args = parser.parse_args()

    # Configure root logger once, here, based on CLI flags.
    # All module loggers (including df_pipeline.*) inherit this config.
    log_level = logging.DEBUG if args.debug else logging.INFO if args.verbose else logging.WARNING
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
        datefmt="%H:%M:%S",
        stream=sys.stdout,
    )

    main(
        config_filename=args.config or DEFAULT_CONFIG,
        dry_run=args.dry_run,
    )