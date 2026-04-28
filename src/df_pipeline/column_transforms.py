"""
Column-level transformations for pandas DataFrames.

This module provides low-level primitives for applying column transforms.
It is decoupled from configuration parsing: functions here work with
:class:`~df_pipeline.schema.ColumnTransform` objects, not raw dicts.

The entry point for most users is :func:`apply_column_transforms`, which
accepts a list of :class:`~df_pipeline.schema.ColumnTransform` objects and
applies them sequentially, each potentially depending on columns created by
previous steps.

Supported operators are defined in :data:`COLUMN_TRANSFORM_MAPPERS`.
"""

from __future__ import annotations

from logging import Logger
from typing import Any, Callable

import pandas as pd

from df_pipeline.schema import ColumnTransform


# ---------------------------------------------------------------------------
# Transform registry
# ---------------------------------------------------------------------------

COLUMN_TRANSFORM_MAPPERS: dict[str, Callable] = {
    # Cast operations
    "to_numeric":  lambda s, _other, p: pd.to_numeric(s, **p),
    "to_datetime": lambda s, _other, p: pd.to_datetime(s, **p),

    # Timezone conversion  (requires params["tz"])
    "tz_convert":  lambda s, _other, p: s.dt.tz_convert(p["tz"]),

    # Binary column arithmetic  (returns float, unit-aware)
    "col_diff":    lambda s, other,  p: (s - other) / pd.Timedelta(1, unit=p.get("unit", "seconds")),
}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _apply_single_transform(
    df: pd.DataFrame,
    ct: ColumnTransform,
) -> pd.DataFrame:
    """
    Apply one :class:`~df_pipeline.schema.ColumnTransform` to a DataFrame.

    Parameters
    ----------
    df : pd.DataFrame
        Input DataFrame. Modified by assignment to ``ct.dest``.
    ct : ColumnTransform
        Transform specification.

    Returns
    -------
    pd.DataFrame
        DataFrame with ``ct.dest`` created or overwritten.

    Raises
    ------
    KeyError
        If ``ct.col`` or ``ct.other_col`` is not found in ``df``.
    KeyError
        If ``ct.op`` is not in :data:`COLUMN_TRANSFORM_MAPPERS`.
    """
    if ct.op not in COLUMN_TRANSFORM_MAPPERS:
        supported = set(COLUMN_TRANSFORM_MAPPERS)
        raise KeyError(
            f'Transform op "{ct.op}" is not supported. '
            f"Choose from: {supported}"
        )

    # Resolve primary series
    try:
        series = df[ct.col_key]
    except KeyError:
        raise KeyError(
            f"Column {ct.col_key!r} not found in DataFrame. "
            f"Available columns: {list(df.columns)}"
        )


    # Resolve secondary series
    if ct.other_col_key is not None:
        try:
            other_series = df[ct.other_col_key]
        except KeyError:
            raise KeyError(
                f"Column {ct.other_col_key!r} not found in DataFrame. "
                f"Available columns: {list(df.columns)}"
            )
    else:
        other_series = None

    dest_col = ct.dest_key or ct.col_key 
    df[dest_col] = COLUMN_TRANSFORM_MAPPERS[ct.op](series, other_series, ct.params)
    return df


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def apply_column_transforms(
    df: pd.DataFrame,
    transforms: list[ColumnTransform],
    logger: Logger | None = None,
) -> pd.DataFrame:
    """
    Apply a sequence of column transforms to a DataFrame.

    Transforms are applied sequentially. Each transform may reference columns
    created by previous transforms in the same list.

    Parameters
    ----------
    df : pd.DataFrame
        Input DataFrame. Modified in place per transform, but the caller
        receives a copy (see :func:`~df_pipeline.transforms.apply_base_transform`).
    transforms : list of ColumnTransform
        Transforms to apply in order.
    logger : logging.Logger, optional
        If provided, debug messages are emitted for each applied transform.

    Returns
    -------
    pd.DataFrame
        DataFrame with all transforms applied.

    Raises
    ------
    KeyError
        If a referenced column does not exist at the time the transform runs.

    Examples
    --------
    Cast and diff::

        from df_pipeline.schema import ColumnTransform
        from df_pipeline.column_transforms import apply_column_transforms

        transforms = [
            ColumnTransform(col="flow_raw", op="to_numeric", dest="flow",
                            params={"errors": "coerce"}),
            ColumnTransform(col="end_dt", other_col="start_dt", op="col_diff",
                            dest="elapsed_days", params={"unit": "days"}),
        ]
        df_out = apply_column_transforms(df, transforms)
    """
    for ct in transforms:
        if logger is not None:
            logger.debug(
                "Column transform: dest=%r, op=%r, col=%r, other_col=%r, params=%r",
                ct.dest, ct.op, ct.col, ct.other_col, ct.params,
            )
        df = _apply_single_transform(df, ct)

    return df