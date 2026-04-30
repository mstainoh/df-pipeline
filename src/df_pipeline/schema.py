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
        ],
        index="well_id",
    )
"""

from __future__ import annotations
from typing import Any, Literal, Optional
from pydantic import BaseModel, model_validator

from df_pipeline.registry import COLUMN_TRANSFORM_REGISTRY, OpName

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
    op : OpName
        Comparison or string operator. Supported values:
        ``ge``, ``gt``, ``le``, ``lt``, ``eq``, ``ne``,
        ``startswith``, ``endswith``, ``contains``.
    value : Any, optional
        Right-hand side scalar. May be ``None`` if ``other_col`` is specified.
    other_col : str or list of str, optional
        Right-hand side column. May be ``None`` if ``value`` is specified.
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
        if isinstance(self.col, list):
            return tuple(self.col)
        return self.col

    @property
    def other_col_key(self) -> Optional[str | tuple]:
        if isinstance(self.other_col, list):
            return tuple(self.other_col)
        return self.other_col


# ---------------------------------------------------------------------------
# ColumnTransform
# ---------------------------------------------------------------------------

class ColumnTransform(BaseModel):
    """
    A single column-level transformation producing a new or overwritten column.

    The ``op`` field is validated at construction time against
    :data:`~df_pipeline.registry.COLUMN_TRANSFORM_REGISTRY`.  Custom ops can
    be registered with :func:`~df_pipeline.registry.register_transform` before
    any ``ColumnTransform`` is instantiated.

    Parameters
    ----------
    col : str or list of str, optional
        Primary input column. Required when ``spec.requires_col`` is ``True``
        (all built-in ops).
    op : str
        Operation name. Must be a key in ``COLUMN_TRANSFORM_REGISTRY``.
        Built-in: ``to_numeric``, ``to_datetime``, ``tz_convert``, ``date_diff``.
    dest : str, optional
        Output column name. If omitted, overwrites ``col``.
    other_col : str or list of str, optional
        Secondary input column. Required for binary ops (e.g. ``date_diff``).
    params : dict, optional
        Extra keyword arguments forwarded to the underlying function.

        Per-op params
        ~~~~~~~~~~~~~
        to_numeric  : errors {"raise", "coerce", "ignore"} — default ``"raise"``
        to_datetime : errors, format, utc — forwarded to :func:`pandas.to_datetime`
        tz_convert  : tz (str, required) — e.g. ``"America/Argentina/Buenos_Aires"``
        date_diff   : unit {"days", "hours", "minutes", "seconds"} — default ``"seconds"``
    """

    col: str | list[str] | None = None
    op: str
    dest: str | None = None
    other_col: str | list[str] | None = None
    params: dict[str, Any] = {}

    @model_validator(mode="after")
    def _validate_op(self) -> ColumnTransform:
        if self.op not in COLUMN_TRANSFORM_REGISTRY:
            supported = set(COLUMN_TRANSFORM_REGISTRY)
            raise ValueError(
                f"op '{self.op}' is not registered. "
                f"Available: {supported}. "
                f"Use register_transform() to add custom ops."
            )

        spec = COLUMN_TRANSFORM_REGISTRY[self.op]

        if spec.requires_col and self.col is None:
            raise ValueError(f"op '{self.op}' requires col")
        if spec.requires_other_col and self.other_col is None:
            raise ValueError(f"op '{self.op}' requires other_col")
        for p in spec.required_params:
            if p not in self.params:
                raise ValueError(f"op '{self.op}' requires params['{p}']")

        return self

    @property
    def col_key(self) -> str | tuple | None:
        if isinstance(self.col, list):
            return tuple(self.col)
        return self.col

    @property
    def dest_key(self) -> str | None:
        return self.dest or (self.col if isinstance(self.col, str) else None)

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

    All fields are optional and default to a no-op.

    Transformation order (matches :func:`~df_pipeline.transforms.apply_base_transform`):

    1. Rename columns       (``renames``)
    2. Assign scalar cols   (``assigns``)
    3. Column transforms    (``column_transforms``)
    4. Filter rows          (``column_filters``)
    5. Drop duplicates      (``drop_duplicates``)
    6. Select columns       (``select``)
    7. Set index            (``index``)

    Parameters
    ----------
    renames : dict of str to str, optional
        Column rename mapping ``{old_name: new_name}``.
    assigns : dict of str to Any, optional
        Columns to create or overwrite with scalar values.
    column_transforms : list of ColumnTransform, optional
        Column-level transforms applied in order.
    column_filters : list of ColumnFilter, optional
        Row filters combined with logical AND.
    drop_duplicates : list of str or bool, optional. Allows MultiIndex columns via list of level names.
        If a list, drop duplicates considering only those columns as subset.
        If ``True``, drop fully duplicate rows. Default ``False`` (skip).
    select : list of (str | list[str]), optional
        Columns to retain in the output. Applied after filters. Allows MultiIndex columns via list of level names.
    index : str or list of str, optional
        Column(s) to set as the DataFrame index.
    """

    renames:           dict[str, str]        = {}
    assigns:           dict[str, Any]        = {}
    column_transforms: list[ColumnTransform] = []
    column_filters:    list[ColumnFilter]    = []
    drop_duplicates:   list[str | list] | bool      = False
    select:            list[str | list[str]]             = []
    index:             str | list[str] | None = None

    @property
    def select_col_keys(self):
        return [tuple(col) if isinstance(col, list) else col for col in self.select]

    @property
    def drop_col_keys(self):
        if isinstance(self.drop_duplicates, list):
            subset = [tuple(col) if isinstance(col, list) else col for col in self.drop_duplicates]
        elif self.drop_duplicates is True:
            subset = True
        else:            
            subset = None
        return subset
