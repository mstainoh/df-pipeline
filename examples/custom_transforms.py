"""
Custom transform ops for the example pipeline.

Call ``register_all()`` once at startup, before any TransformConfig
is instantiated, so that Pydantic can validate custom op names.

Usage
-----
::

    import examples.custom_transforms as custom
    custom.register_all()

    # now "unit_convert" is a valid op in YAML and ColumnTransform
"""

from df_pipeline.registry import TransformSpec, register_transform
import pandas as pd

def _unit_convert(s1: pd.Series, s2=None, factor: float = 1.0, **kwargs) -> pd.Series:
    """Scale a numeric series by a constant factor.
    
    Typical use: flow unit conversion (m³/h → L/s uses factor=1/3.6).
    """
    return s1 * factor

def set_now(*args, **kwargs):
    """Return a Series of the current timestamp, aligned with the input series."""
    # We ignore the input series and just return the current time for all rows.
    return pd.Timestamp.now()



CUSTOM_TRANSFORMS = {
    "unit_convert": TransformSpec(fn=_unit_convert),
    "now": TransformSpec(fn=set_now, requires_col=False)
}


def register_all() -> None:
    """Register all custom ops into the global registry."""
    for name, spec in CUSTOM_TRANSFORMS.items():
        register_transform(name, spec)
