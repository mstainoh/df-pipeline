"""
Transform registry for column-level operations.

This module is intentionally free of dependencies on other ``df_pipeline``
modules to avoid circular imports.  Both :mod:`df_pipeline.schema` and
:mod:`df_pipeline.column_transforms` import from here.

Built-in ops
------------
- ``to_numeric``  — cast to numeric  (wraps :func:`pandas.to_numeric`)
- ``to_datetime`` — cast to datetime (wraps :func:`pandas.to_datetime`)
- ``tz_convert``  — timezone conversion (requires ``params.tz``)
- ``date_diff``   — signed difference between two datetime columns,
                    returns a float in the requested ``unit``

Registering custom ops
----------------------
::

    from df_pipeline.registry import TransformSpec, register_transform

    register_transform("m3h_to_ls", TransformSpec(
        fn=lambda s1, s2=None, factor=1/3.6, **kwargs: s1 * factor,
    ))
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Literal, Any
import operator
import pandas as pd

# ---------------------------------------------------------------------------
# Supported filter operators
# ---------------------------------------------------------------------------

OpName = Literal[
    "ge", "gt", "le", "lt", "eq", "ne",
    "startswith", "endswith", "contains",
    "in", "nin"
]
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

    # other
    "in": lambda s, x: s.isin(x),
    "nin":  lambda s, x: ~s.isin(x),
}
# ---------------------------------------------------------------------------
# TransformSpec
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class TransformSpec:
    """
    Metadata + callable implementation for a single column transform op.

    Parameters
    ----------
    fn : Callable
        Core function with signature ``(s1, s2=None, **kwargs) -> pd.Series``.
        ``s1`` is the primary series, ``s2`` the secondary (binary ops only).
        All YAML ``params`` are forwarded as ``**kwargs``.
    requires_col : bool
        Whether the op requires a primary column ``col``. Default ``True``.
    requires_other_col : bool
        Whether the op requires a secondary column ``other_col``. Default ``False``.
    required_params : frozenset of str
        Keys that must be present in ``params`` at config validation time.

    Examples
    --------
    ::

        spec = TransformSpec(
            fn=lambda s1, s2=None, factor=1.0, **kw: s1 * factor,
        )
        result = spec(series)
    """
    fn:                 Callable
    requires_col:       bool = True
    requires_other_col: bool = False
    required_params:    frozenset[str] = frozenset()

    def __call__(
        self,
        s1: pd.Series | None = None,
        s2: pd.Series | None = None,
        **kwargs,
    ) -> pd.Series:
        args = [] + [s1] * self.requires_col + [s2] * self.requires_other_col
        return self.fn(*args, **kwargs)


# ---------------------------------------------------------------------------
# Built-in registry
# ---------------------------------------------------------------------------
COLUMN_TRANSFORM_REGISTRY: dict[str, TransformSpec] = {
    "to_numeric": TransformSpec(
        fn=lambda s1, s2=None, **kwargs: pd.to_numeric(s1, **kwargs),
    ),
    "to_datetime": TransformSpec(
        fn=lambda s1, s2=None, **kwargs: pd.to_datetime(s1, **kwargs),
    ),
    "tz_convert": TransformSpec(
        fn=lambda s1, s2=None, tz=None, **kwargs: s1.dt.tz_convert(tz),
        required_params=frozenset({"tz"}),
    ),
    "date_diff": TransformSpec(
        fn=lambda s1, s2, unit="seconds", **kwargs: (s1 - s2) / pd.Timedelta(1, unit=unit), #type:ignore
        requires_other_col=True,
    ),
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def register_transform(name: str, spec: TransformSpec) -> None:
    """
    Register a custom transform op at runtime.

    Parameters
    ----------
    name : str
        Op name used in YAML and :class:`~df_pipeline.schema.ColumnTransform`.
    spec : TransformSpec
        Implementation and metadata.

    Raises
    ------
    TypeError
        If ``spec`` is not a :class:`TransformSpec` instance.

    Examples
    --------
    ::

        from df_pipeline.registry import TransformSpec, register_transform

        register_transform("apply_factor", TransformSpec(
            fn=lambda s1, *, factor=1.0, **kwargs: s1 * factor,
        ))
    """
    if not isinstance(spec, TransformSpec):
        raise TypeError(f"spec must be a TransformSpec, got {type(spec).__name__}")
    COLUMN_TRANSFORM_REGISTRY[name] = spec
