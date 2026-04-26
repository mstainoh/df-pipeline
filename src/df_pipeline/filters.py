"""
Boolean mask construction for pandas DataFrames.

This module provides low-level primitives for building row filters.
It is decoupled from configuration parsing: functions here work with
plain Python types, not with Pydantic models or YAML dicts.

The entry point for most users is :func:`build_mask`, which accepts a
list of :class:`~df_pipeline.schema.ColumnFilter` objects and combines them
with logical AND.

Supported operators are defined in :data:`OP_MAPPERS`.
"""

from __future__ import annotations

import operator
from logging import Logger
from typing import Any

import pandas as pd

from df_pipeline.schema import ColumnFilter


# ---------------------------------------------------------------------------
# Operator registry
# ---------------------------------------------------------------------------

OP_MAPPERS: dict[str, Any] = {
    # Numerical comparisons
    "ge": operator.ge,
    "gt": operator.gt,
    "le": operator.le,
    "lt": operator.lt,
    "eq": operator.eq,
    "ne": operator.ne,

    # Vectorized string operations
    "startswith": lambda s, x: s.astype(str).str.startswith(x),
    "endswith":   lambda s, x: s.astype(str).str.endswith(x),
    "contains":   lambda s, x: s.astype(str).str.contains(x, regex=False),
}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _get_op_mask(series: pd.Series, op_name: str, value: Any) -> pd.Series:
    """
    Apply a single operator to a Series and return a boolean mask.

    Parameters
    ----------
    series : pd.Series
        Input Series on which the filter is applied.
    op_name : str
        Operator name. Must be a key in :data:`OP_MAPPERS`.
    value : Any
        Right-hand side of the operation.

    Returns
    -------
    pd.Series
        Boolean mask aligned with ``series.index``.

    Raises
    ------
    KeyError
        If ``op_name`` is not in :data:`OP_MAPPERS`.
    TypeError
        If the operator does not return a boolean pandas Series.
    """
    if op_name not in OP_MAPPERS:
        supported = set(OP_MAPPERS)
        raise KeyError(
            f'Operator "{op_name}" is not supported. '
            f"Choose from: {supported}"
        )

    mask = OP_MAPPERS[op_name](series, value)

    if not isinstance(mask, pd.Series):
        raise TypeError(
            f"Operator '{op_name}' must return a pandas Series, "
            f"got {type(mask).__name__}"
        )
    if mask.dtype != bool:
        raise TypeError(
            f"Mask returned by '{op_name}' must be boolean, "
            f"got dtype '{mask.dtype}'"
        )

    return mask


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def build_mask(
    df: pd.DataFrame,
    filters: list[ColumnFilter],
    logger: Logger | None = None,
) -> pd.Series:
    """
    Build a boolean mask from a list of column filters.

    Filters are combined with logical AND. An empty filter list returns
    a mask of all ``True``.

    Parameters
    ----------
    df : pd.DataFrame
        Input DataFrame. Supports both flat and MultiIndex columns.
    filters : list of ColumnFilter
        Filters to apply. Each filter targets one column (or MultiIndex
        column path) with a single operator.
    logger : logging.Logger, optional
        If provided, debug messages are emitted for each applied filter.

    Returns
    -------
    pd.Series
        Boolean mask aligned with ``df.index``.

    Raises
    ------
    KeyError
        If a referenced column does not exist in ``df``.

    Examples
    --------
    Flat columns::

        from df_pipeline.schema import ColumnFilter
        from df_pipeline.filters import build_mask

        filters = [
            ColumnFilter(col="rate", op="gt", value=100),
            ColumnFilter(col="well_id", op="startswith", value="PW"),
        ]
        mask = build_mask(df, filters)
        df_filtered = df[mask]

    MultiIndex columns::

        filters = [
            ColumnFilter(col=["measurement", "temperature"], op="ge", value=20.0),
        ]
        mask = build_mask(df, filters)
    """
    mask = pd.Series(True, index=df.index)

    for f in filters:
        col_key = f.col_key

        if logger is not None:
            logger.debug(f"Applying filter: col={col_key!r}, op={f.op!r}, value={f.value!r}")

        try:
            series = df[col_key]
        except KeyError:
            raise KeyError(
                f"Column {col_key!r} not found in DataFrame. "
                f"Available columns: {list(df.columns)}"
            )

        mask &= _get_op_mask(series, f.op, f.value)

    return mask
