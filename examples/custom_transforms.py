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


def unit_convert(s1, *, factor=1):
    """Convert flow rate from m³/h to L/s  (divide by 3.6)."""
    return s1 * factor


CUSTOM_TRANSFORMS = {
    "unit_convert": TransformSpec(fn=unit_convert),
}


def register_all() -> None:
    """Register all custom ops into the global registry."""
    for name, spec in CUSTOM_TRANSFORMS.items():
        register_transform(name, spec)
