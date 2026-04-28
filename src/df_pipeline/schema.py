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

from typing import Any, Literal, Optional

from pydantic import BaseModel, model_validator

# ---------------------------------------------------------------------------
# aux functions
# ---------------------------------------------------------------------------
def str_or_tuple(s: Optional[str | tuple[str]]=None) -> Optional[str | tuple]:
    if isinstance(s, list):
        return tuple(s)
    return s


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
        Right-hand side of the comparison (value). May be ``None`` if "other" is specified .
    other_col : str or list of str, optional
        Right-hand side of the comparison (column). May be ``None`` if "value" is specified
    """

    col: str | list[str]
    op: OpName
    value: Any = None
    other_col: Optional[str | list[str]] = None

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

    @property
    def other_col_key(self) -> Optional[str | tuple]:
        """
        Column accessor compatible with ``df[key]``.

        Returns a ``tuple`` for MultiIndex columns, a plain ``str`` otherwise (or ``None`` if other_col is not defined).
        """
        if isinstance(self.other_col, list):
            return tuple(self.other_col)
        return self.other_col


# ---------------------------------------------------------------------------
# Column transformations
# ---------------------------------------------------------------------------

ColumnTransformOp = Literal[
    "to_numeric",
    "to_datetime", 
    "tz_convert",
    "col_diff",
]

class ColumnTransform(BaseModel):
    """
    A single column-level transformation producing a new or overwritten column.

    Parameters
    ----------
    col : str or list[str]
        Primary input column. Required for all ops except nullary ones.
    dest : str or list[str], optional
        Output column name. Created if absent, overwritten if present.
    op : ColumnTransformOp
        Operation to apply.
    other_col : str or list[str], optional
        Secondary input column. Required for binary ops (col_diff).
    params : dict, optional
        Extra keyword arguments forwarded to the underlying function.

        Per-op params
        ~~~~~~~~~~~~~
        to_numeric  : errors {"raise","coerce","ignore"} — default "raise"
        to_datetime : errors, format, utc  — forwarded to pd.to_datetime
        tz_convert  : tz (str, required)   — e.g. "America/Argentina/Buenos_Aires"
        col_diff    : unit {"days","hours","minutes","seconds"} — default "seconds"
    """
    col: str | list[str]
    op: ColumnTransformOp
    dest: str | list[str] | None = None
    other_col: str | list[str] | None = None
    params: dict[str, Any] = {}

    @model_validator(mode="after")
    def _validate_operands(self) -> ColumnTransform:
        unary_ops  = {"to_numeric", "to_datetime", "tz_convert"}
        binary_ops = {"col_diff"}

        if self.op in unary_ops and self.col is None:
            raise ValueError(f"op '{self.op}' requires col")
        if self.op in binary_ops and (self.col is None or self.other_col is None):
            raise ValueError(f"op '{self.op}' requires both col and other_col")
        if self.op == "tz_convert" and "tz" not in self.params:
            raise ValueError("op 'tz_convert' requires params.tz")
        return self

    @property
    def col_key(self) -> str | tuple:
        if isinstance(self.col, list):
            return tuple(self.col)
        return self.col

    @property
    def dest_key(self) -> str | tuple | None:
        if isinstance(self.dest, list):
            return tuple(self.dest)
        return self.dest

    @property
    def other_col_key(self) -> str | tuple | None:
        if isinstance(self.other_col, list):
            return tuple(self.other_col)
        return self.other_col

# ---------------------------------------------------------------------------
# TransformConfig
# ---------------------------------------------------------------------------

class TransformConfig(BaseModel):
    """
    Full declarative specification for a DataFrame transformation pipeline.

    All fields are optional and default to a no-op, so a config that only
    renames columns does not need to specify ``column_filters`` etc.

    The transformation order matches :func:`df_pipeline.transforms.apply_base_transform`:

    1. Rename columns
    2. Assign new columns
    3. Column transformations
    4. Filter rows
    5. Select columns
    6. Set index

    Parameters
    ----------
    renames : dict of str to str, optional
        Column rename mapping ``{old_name: new_name}``.
    assigns : dict of str to Any, optional
        Columns to create or overwrite with scalar or array-like values.
    column_transforms: list of ColumnTransform, optional
        Column transformations operations
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
    column_transforms: list[ColumnTransform] = []
    column_filters: list[ColumnFilter] = []
    select: list[str] = []
    index: str | list[str] | None = None
