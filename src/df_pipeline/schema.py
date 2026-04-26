"""
Pydantic models for declarative ETL transform configuration.

These models are the canonical representation of the ``transform`` block
in a YAML config file. They can also be constructed programmatically,
making the library usable without YAML at all.

Usage from YAML
---------------
::

    import yaml
    from df_pipeline.schema import TransformConfig

    with open("config.yaml") as f:
        params = yaml.safe_load(f)

    config = TransformConfig.model_validate(params["transform"]["data"])

Usage from Python
-----------------
::

    from df_pipeline.schema import TransformConfig, ColumnFilter

    config = TransformConfig(
        column_filters=[
            ColumnFilter(col="well_id", op="startswith", value="PW"),
            ColumnFilter(col=["measurement", "temperature"], op="ge", value=20.0),
        ],
        index="well_id",
    )
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, model_validator


# ---------------------------------------------------------------------------
# Supported operators
# ---------------------------------------------------------------------------

OpName = Literal[
    "ge", "gt", "le", "lt", "eq", "ne",
    "startswith", "endswith", "contains",
]


# ---------------------------------------------------------------------------
# ColumnFilter
# ---------------------------------------------------------------------------

class ColumnFilter(BaseModel):
    """
    A single row filter applied to one DataFrame column.

    Parameters
    ----------
    col : str or list of str
        Column name, or a list of level names for MultiIndex columns.
        Examples: ``"well_id"``, ``["measurement", "temperature"]``.
    op : OpName
        Comparison or string operator. Supported values:
        ``ge``, ``gt``, ``le``, ``lt``, ``eq``, ``ne``,
        ``startswith``, ``endswith``, ``contains``.
    value : Any, optional
        Right-hand side of the comparison. May be ``None`` for operators
        that do not require a value (e.g. null checks in future extensions).
    """

    col: str | list[str]
    op: OpName
    value: Any = None

    @model_validator(mode="after")
    def _col_not_empty(self) -> ColumnFilter:
        if isinstance(self.col, list) and len(self.col) == 0:
            raise ValueError("col must not be an empty list")
        if isinstance(self.col, str) and not self.col.strip():
            raise ValueError("col must not be an empty string")
        return self

    @property
    def col_key(self) -> str | tuple:
        """
        Column accessor compatible with ``df[key]``.

        Returns a ``tuple`` for MultiIndex columns, a plain ``str`` otherwise.
        """
        if isinstance(self.col, list):
            return tuple(self.col)
        return self.col


# ---------------------------------------------------------------------------
# TransformConfig
# ---------------------------------------------------------------------------

class TransformConfig(BaseModel):
    """
    Full declarative specification for a DataFrame transformation pipeline.

    All fields are optional and default to a no-op, so a config that only
    renames columns does not need to specify ``column_filters`` etc.

    The transformation order matches :func:`df_pipeline.transforms.apply_transform`:

    1. Rename columns
    2. Assign new columns
    3. Filter rows
    4. Select columns
    5. Set index

    Parameters
    ----------
    renames : dict of str to str, optional
        Column rename mapping ``{old_name: new_name}``.
    assigns : dict of str to Any, optional
        Columns to create or overwrite with scalar or array-like values.
    column_filters : list of ColumnFilter, optional
        Row filters combined with logical AND.
    select : list of str, optional
        Columns to retain in the output. Applied after filters.
    index : str or list of str, optional
        Column(s) to set as the DataFrame index.

    Examples
    --------
    Construct from a raw dict (e.g. parsed YAML)::

        config = TransformConfig.model_validate({
            "renames": {"old_col": "new_col"},
            "column_filters": [
                {"col": "well_id", "op": "startswith", "value": "PW"},
                {"col": ["meas", "temp"], "op": "ge", "value": 20.0},
            ],
            "index": "well_id",
        })

    Construct programmatically::

        config = TransformConfig(
            renames={"old_col": "new_col"},
            column_filters=[
                ColumnFilter(col="well_id", op="startswith", value="PW"),
            ],
            index="well_id",
        )
    """

    renames: dict[str, str] = {}
    assigns: dict[str, Any] = {}
    column_filters: list[ColumnFilter] = []
    select: list[str] = []
    index: str | list[str] | None = None
