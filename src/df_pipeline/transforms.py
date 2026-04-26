"""
Declarative DataFrame transformation pipeline.

The main entry point is :func:`apply_transform`, which executes a
fixed-order sequence of operations driven by a :class:`~df_pipeline.schema.TransformConfig`.

Transformation order
--------------------
1. Rename columns  (``renames``)
2. Assign new columns  (``assigns``)
3. Filter rows  (``column_filters``)
4. Select columns  (``select``)
5. Set index  (``index``)

The order is intentional:

- Renames happen first so that subsequent steps can use the new names.
- Assigns happen before filters so that derived columns can be filtered on.
- Select happens after filters to avoid dropping columns needed for filtering.
"""

from __future__ import annotations

from logging import Logger

import pandas as pd

from df_pipeline.filters import build_mask
from df_pipeline.schema import TransformConfig


def apply_transform(
    df: pd.DataFrame,
    config: TransformConfig,
    logger: Logger | None = None,
) -> pd.DataFrame:
    """
    Apply a declarative transformation pipeline to a DataFrame.

    Parameters
    ----------
    df : pd.DataFrame
        Input DataFrame. Not modified in place.
    config : TransformConfig
        Transformation specification. All fields are optional;
        omitted steps are skipped.
    logger : logging.Logger, optional
        If provided, debug messages are emitted at each step.

    Returns
    -------
    pd.DataFrame
        Transformed DataFrame.

    Examples
    --------
    From a Pydantic model::

        from df_pipeline.schema import TransformConfig, ColumnFilter
        from df_pipeline.transforms import apply_transform

        config = TransformConfig(
            renames={"old": "new"},
            column_filters=[ColumnFilter(col="well_id", op="startswith", value="PW")],
            index="well_id",
        )
        df_out = apply_transform(df_raw, config)

    From parsed YAML::

        import yaml
        from df_pipeline.schema import TransformConfig
        from df_pipeline.transforms import apply_transform

        params = yaml.safe_load(open("config.yaml"))
        config = TransformConfig.model_validate(params["transform"]["data"])
        df_out = apply_transform(df_raw, config)
    """
    df = df.copy()

    if config.renames:
        if logger is not None:
            logger.debug("Transform step 1/5 — renaming columns: %s", config.renames)
        df = df.rename(columns=config.renames)

    if config.assigns:
        if logger is not None:
            logger.debug("Transform step 2/5 — assigning columns: %s", list(config.assigns))
        for col, value in config.assigns.items():
            df[col] = value

    if config.column_filters:
        if logger is not None:
            logger.debug(
                "Transform step 3/5 — applying %d filter(s)", len(config.column_filters)
            )
        mask = build_mask(df, config.column_filters, logger=logger)
        df = df[mask]

    if config.select:
        if logger is not None:
            logger.debug("Transform step 4/5 — selecting columns: %s", config.select)
        df = df[config.select]

    if config.index is not None:
        if logger is not None:
            logger.debug("Transform step 5/5 — setting index: %s", config.index)
        df = df.set_index(config.index)

    return df
