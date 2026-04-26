"""
df_pipeline — declarative DataFrame transformation utilities.

Public API
----------

Schema (config models)::

    from df_pipeline import TransformConfig, ColumnFilter

Transforms::

    from df_pipeline import apply_transform

Filters::

    from df_pipeline import build_mask

CLI helpers::

    from df_pipeline import log_runner, default_parser
"""

from df_pipeline.schema import ColumnFilter, TransformConfig
from df_pipeline.filters import build_mask
from df_pipeline.transforms import apply_transform
from df_pipeline.cli import log_runner, default_parser
import logging

__all__ = [
    "ColumnFilter",
    "TransformConfig",
    "build_mask",
    "apply_transform",
    "log_runner",
    "default_parser",
]

 
# Package-level logger. NullHandler by default — the caller decides
# whether and how to configure logging. To see debug output:
#
#     import logging
#     logging.getLogger("df_pipeline").setLevel(logging.DEBUG)
#
logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())
 