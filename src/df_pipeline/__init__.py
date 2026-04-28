"""
df_pipeline — declarative DataFrame transformation utilities.

Public API
----------

Schema (config models)::

    from df_pipeline import TransformConfig, ColumnFilter

Transforms::

    from df_pipeline import apply_base_transform

Filters::

    from df_pipeline import build_mask

CLI helpers::

    from df_pipeline import log_runner, default_parser
"""

from df_pipeline.schema import ColumnFilter, TransformConfig
from df_pipeline.filters import build_mask
from df_pipeline.transforms import apply_base_transform
from df_pipeline.cli import log_runner, default_parser
# import logging
from df_pipeline.registry import TransformSpec, register_transform, COLUMN_TRANSFORM_REGISTRY
from df_pipeline.column_transforms import apply_column_transforms
from df_pipeline.schema import ColumnFilter, ColumnTransform, TransformConfig

__all__ = [
    # schema
    "ColumnFilter",
    "ColumnTransform",
    "TransformConfig",
    
    # transforms
    "apply_base_transform",
    "apply_column_transforms",
    
    # filters
    "build_mask",
    
    # registry
    "TransformSpec",
    "register_transform",
    "COLUMN_TRANSFORM_REGISTRY",
    
    # cli
    "log_runner",
    "default_parser",
]
 