"""
Declarative DataFrame transformation pipeline.

The main entry point is :func:`apply_base_transform`, which executes a
fixed-order sequence of operations driven by a
:class:`~df_pipeline.schema.TransformConfig`.

Transformation order
--------------------
1. Rename columns       (``renames``)
2. Assign scalar cols   (``assigns``)
3. Column transforms    (``column_transforms``)
4. Filter rows          (``column_filters``)
5. Drop duplicates      (``drop_duplicates``)
6. Select columns       (``select``)
7. Set index            (``index``)

The order is intentional:

- Renames happen first so that subsequent steps can use the new names.
- Assigns happen before column_transforms so derived scalars are available.
- Column transforms happen before filters so computed cols can be filtered on.
- Drop duplicates happens after filters to work on the reduced row set.
- Select happens after filters to avoid dropping cols needed for filtering.
"""

from __future__ import annotations

from logging import Logger

import pandas as pd

from df_pipeline.filters import build_mask
from df_pipeline.schema import TransformConfig
from df_pipeline.column_transforms import apply_column_transforms

def _list_to_tuple(cols: list[str] | list) -> list[str | tuple]:
    return [tuple(col) if isinstance(col, list) else col for col in cols]

def apply_base_transform(
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
        from df_pipeline.transforms import apply_base_transform

        config = TransformConfig(
            renames={"old": "new"},
            column_filters=[ColumnFilter(col="node_id", op="startswith", value="N0")],
            index="node_id",
        )
        df_out = apply_base_transform(df_raw, config)

    From parsed YAML::

        import yaml
        from df_pipeline.schema import TransformConfig
        from df_pipeline.transforms import apply_base_transform

        params = yaml.safe_load(open("config.yaml"))
        config = TransformConfig.model_validate(params["transform"]["data"])
        df_out = apply_base_transform(df_raw, config)
    """
    df = df.copy()

    # Step 1 — renames
    if config.renames:
        if logger is not None:
            logger.debug("Transform step 1/8 — renaming columns: %s", config.renames)
        df = df.rename(columns=config.renames)

    # Step 2 — assigns
    if config.assigns:
        if logger is not None:
            logger.debug("Transform step 2/8 — assigning columns: %s", list(config.assigns))
        for col, value in config.assigns.items():
            df[col] = value

    # Step 3 — column transforms
    if config.column_transforms:
        if logger is not None:
            logger.debug(
                "Transform step 3/8 — applying %d column transform(s)",
                len(config.column_transforms),
            )
        df = apply_column_transforms(df, config.column_transforms, logger=logger)

    # Step 4 — row filters
    if config.column_filters:
        if logger is not None:
            logger.debug(
                "Transform step 4/8 — applying %d filter(s)",
                len(config.column_filters),
            )
        mask = build_mask(df, config.column_filters, logger=logger)
        df = df[mask]

    # Step 5 — drop duplicates
    if config.drop_duplicates is not False:
        if logger is not None:
            s = 'subset: {}'.format(config.drop_duplicates) if isinstance(config.drop_duplicates, list) else 'all columns'
            logger.debug("Transform step 5/8 — dropping duplicates - {}".format(s))
        if config.drop_duplicates is True:
            df = df.drop_duplicates()
        else:
            cols = _list_to_tuple(config.drop_duplicates)
            df = df.drop_duplicates(subset=cols)

    # Step 6 — select
    if config.select:
        if logger is not None:
            logger.debug("Transform step 6/8 — selecting columns: %s", config.select)
        cols = _list_to_tuple(config.select)
        df = df[cols]

    # Step 7 — sort
    if config.sort is not None:
        if logger is not None:
            logger.debug("Transform step 7/8 — sorting by columns: %s", config.sort)
        cols = config.sort
        df = df.sort_values(by=cols)

    # Step 8 — set index
    if config.index is not None:
        if logger is not None:
            logger.debug("Transform step 7/7 — setting index: %s", config.index)
        df = df.set_index(config.index)

    return df
