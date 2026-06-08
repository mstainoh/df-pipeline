"""
tests/test_select_dtypes.py

pytest coverage for the select_dtypes step in TransformConfig /
apply_base_transform.

Run with:
    pytest tests/test_select_dtypes.py -v
"""

import pytest
import pandas as pd
import numpy as np
from pydantic import ValidationError

from df_pipeline.schema import TransformConfig
from df_pipeline.transforms import apply_base_transform


# ── fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def mixed_df() -> pd.DataFrame:
    """DataFrame with int, float, object, and bool columns."""
    return pd.DataFrame({
        "int_col":   [1, 2, 3],
        "float_col": [1.1, 2.2, 3.3],
        "str_col":   ["a", "b", "c"],
        "bool_col":  [True, False, True],
    })


# ── schema validation ─────────────────────────────────────────────────────────

class TestSelectDtypesSchema:

    def test_empty_dict_is_valid(self):
        cfg = TransformConfig(select_dtypes={})
        assert cfg.select_dtypes == {}

    def test_include_string(self):
        cfg = TransformConfig(select_dtypes={"include": "number"})
        assert cfg.select_dtypes == {"include": "number"}

    def test_include_list(self):
        cfg = TransformConfig(select_dtypes={"include": ["float64", "int64"]})
        assert cfg.select_dtypes["include"] == ["float64", "int64"]

    def test_exclude_string(self):
        cfg = TransformConfig(select_dtypes={"exclude": "object"})
        assert cfg.select_dtypes == {"exclude": "object"}

    def test_include_and_exclude(self):
        cfg = TransformConfig(select_dtypes={"include": "number", "exclude": None})
        assert cfg.select_dtypes["include"] == "number"

    def test_unknown_key_rejected(self):
        """extra='forbid' on the parent model should reject unknown top-level keys,
        but select_dtypes values are a plain dict — validate the key manually."""
        with pytest.raises((ValidationError, ValueError)):
            TransformConfig(select_dtypes={"bad_key": "number"})  # type: ignore[arg-type]


# ── transform behaviour ───────────────────────────────────────────────────────

class TestSelectDtypesTransform:

    def test_include_number_keeps_numeric(self, mixed_df):
        cfg = TransformConfig(select_dtypes={"include": "number"})
        out = apply_base_transform(mixed_df, cfg)
        assert set(out.columns) == {"int_col", "float_col"}

    def test_include_list_keeps_listed_dtypes(self, mixed_df):
        cfg = TransformConfig(select_dtypes={"include": ["float64"]})
        out = apply_base_transform(mixed_df, cfg)
        assert list(out.columns) == ["float_col"]

    def test_exclude_object_drops_strings(self, mixed_df):
        cfg = TransformConfig(select_dtypes={"exclude": "object"})
        out = apply_base_transform(mixed_df, cfg)
        assert "str_col" not in out.columns
        assert "int_col" in out.columns

    def test_empty_select_dtypes_is_noop(self, mixed_df):
        cfg = TransformConfig(select_dtypes={})
        out = apply_base_transform(mixed_df, cfg)
        assert list(out.columns) == list(mixed_df.columns)

    def test_select_dtypes_before_select(self, mixed_df):
        """select_dtypes (step 6) runs before select (step 7)."""
        cfg = TransformConfig(
            select_dtypes={"include": "number"},
            select=["float_col"],
        )
        out = apply_base_transform(mixed_df, cfg)
        assert list(out.columns) == ["float_col"]

    def test_select_dtypes_after_filter(self, mixed_df):
        """Filters (step 4) run before select_dtypes (step 6)."""
        from df_pipeline.schema import ColumnFilter
        cfg = TransformConfig(
            column_filters=[ColumnFilter(col="int_col", op="ge", value=2)],
            select_dtypes={"include": "number"},
        )
        out = apply_base_transform(mixed_df, cfg)
        assert len(out) == 2                      # rows 2 and 3
        assert "str_col" not in out.columns

    def test_row_count_preserved(self, mixed_df):
        """select_dtypes only drops columns, never rows."""
        cfg = TransformConfig(select_dtypes={"include": "number"})
        out = apply_base_transform(mixed_df, cfg)
        assert len(out) == len(mixed_df)

    def test_original_df_not_mutated(self, mixed_df):
        original_cols = list(mixed_df.columns)
        cfg = TransformConfig(select_dtypes={"include": "number"})
        apply_base_transform(mixed_df, cfg)
        assert list(mixed_df.columns) == original_cols