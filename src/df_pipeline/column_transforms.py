"""
Column-level transformations for pandas DataFrames.

This module provides low-level primitives for applying column transforms.
It is decoupled from configuration parsing: functions here work with
:class:`~df_pipeline.schema.ColumnTransform` objects, not raw dicts.

The entry point for most users is :func:`apply_column_transforms`, which
accepts a list of :class:`~df_pipeline.schema.ColumnTransform` objects and
applies them sequentially, each potentially depending on columns created by
previous steps.

Supported operators are defined in
:data:`~df_pipeline.registry.COLUMN_TRANSFORM_REGISTRY`.
"""

from __future__ import annotations

from logging import Logger

import pandas as pd

from df_pipeline.registry import COLUMN_TRANSFORM_REGISTRY
from df_pipeline.schema import ColumnTransform


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
        Input DataFrame.
    ct : ColumnTransform
        Transform specification. ``op`` is guaranteed valid by Pydantic.

    Returns
    -------
    pd.DataFrame
        DataFrame with ``ct.dest_key`` created or overwritten.

    Raises
    ------
    KeyError
        If ``ct.col`` or ``ct.other_col`` is not found in ``df``.
    """
    spec = COLUMN_TRANSFORM_REGISTRY[ct.op]  # guaranteed valid by Pydantic

    # Resolve primary series
    s1: pd.Series | None = None
    if spec.requires_col:
        try:
            s1 = df[ct.col_key]
        except KeyError:
            raise KeyError(
                f"Column {ct.col_key!r} not found in DataFrame. "
                f"Available columns: {list(df.columns)}"
            )

    # Resolve secondary series
    s2: pd.Series | None = None
    if spec.requires_other_col:
        try:
            s2 = df[ct.other_col_key]
        except KeyError:
            raise KeyError(
                f"Column {ct.other_col_key!r} not found in DataFrame. "
                f"Available columns: {list(df.columns)}"
            )

    df[ct.dest_key] = spec(s1, s2, **ct.params)
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
        Input DataFrame. Caller is responsible for passing a copy if
        immutability is required (handled by
        :func:`~df_pipeline.transforms.apply_base_transform`).
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
    ::

        from df_pipeline.schema import ColumnTransform
        from df_pipeline.column_transforms import apply_column_transforms

        transforms = [
            ColumnTransform(col="flow_m3h", op="m3h_to_ls", dest="flow_ls"),
            ColumnTransform(col="end_dt", other_col="start_dt", op="date_diff",
                            dest="elapsed_days", params={"unit": "days"}),
        ]
        df_out = apply_column_transforms(df, transforms)
    """
    for ct in transforms:
        if logger is not None:
            logger.debug(
                "Column transform: dest=%r, op=%r, col=%r, other_col=%r, params=%r",
                ct.dest_key, ct.op, ct.col, ct.other_col, ct.params,
            )
        df = _apply_single_transform(df, ct)

    return df
