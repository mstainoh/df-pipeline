"""
Tests for df_pipeline.transforms — apply_base_transform pipeline.
"""

import pandas as pd
import pytest

from df_pipeline.schema import ColumnFilter, TransformConfig
from df_pipeline.transforms import apply_base_transform


# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------

@pytest.fixture
def df() -> pd.DataFrame:
    return pd.DataFrame({
        "well_id":  ["PW001", "PW002", "INJ001", "PW003"],
        "rate":     [120.0,   80.0,    150.0,    95.0],
        "old_name": [1,       2,       3,        4],
    })


# ---------------------------------------------------------------------------
# Individual steps
# ---------------------------------------------------------------------------

class TestRenames:
    def test_rename_column(self, df):
        config = TransformConfig(renames={"old_name": "new_name"})
        out = apply_base_transform(df, config)
        assert "new_name" in out.columns
        assert "old_name" not in out.columns

    def test_no_renames_is_noop(self, df):
        config = TransformConfig()
        out = apply_base_transform(df, config)
        assert list(out.columns) == list(df.columns)


class TestAssigns:
    def test_assign_scalar(self, df):
        config = TransformConfig(assigns={"source": "LIMS"})
        out = apply_base_transform(df, config)
        assert (out["source"] == "LIMS").all()

    def test_assign_overwrites_existing(self, df):
        config = TransformConfig(assigns={"rate": 0.0})
        out = apply_base_transform(df, config)
        assert (out["rate"] == 0.0).all()

    def test_assign_null(self, df):
        config = TransformConfig(assigns={"flag": None})
        out = apply_base_transform(df, config)
        assert out["flag"].isna().all()


class TestFilters:
    def test_filter_reduces_rows(self, df):
        config = TransformConfig(
            column_filters=[ColumnFilter(col="well_id", op="startswith", value="PW")]
        )
        out = apply_base_transform(df, config)
        assert len(out) == 3
        assert "INJ001" not in out["well_id"].values

    def test_empty_filters_keeps_all_rows(self, df):
        config = TransformConfig(column_filters=[])
        out = apply_base_transform(df, config)
        assert len(out) == len(df)


class TestSelect:
    def test_select_columns(self, df):
        config = TransformConfig(select=["well_id", "rate"])
        out = apply_base_transform(df, config)
        assert list(out.columns) == ["well_id", "rate"]

    def test_select_missing_column_raises(self, df):
        config = TransformConfig(select=["well_id", "nonexistent"])
        with pytest.raises(KeyError):
            apply_base_transform(df, config)


class TestIndex:
    def test_set_index(self, df):
        config = TransformConfig(index="well_id")
        out = apply_base_transform(df, config)
        assert out.index.name == "well_id"
        assert "well_id" not in out.columns

    def test_set_multiindex(self, df):
        config = TransformConfig(index=["well_id", "old_name"])
        out = apply_base_transform(df, config)
        assert out.index.names == ["well_id", "old_name"]


# ---------------------------------------------------------------------------
# Pipeline ordering
# ---------------------------------------------------------------------------

class TestPipelineOrdering:
    def test_rename_before_filter(self, df):
        """Filter on the renamed column name, not the original."""
        config = TransformConfig(
            renames={"well_id": "id"},
            column_filters=[ColumnFilter(col="id", op="startswith", value="PW")],
        )
        out = apply_base_transform(df, config)
        assert len(out) == 3

    def test_assign_before_filter(self, df):
        """Filter on an assigned column."""
        config = TransformConfig(
            assigns={"flag": True},
            column_filters=[ColumnFilter(col="flag", op="eq", value=True)],
        )
        out = apply_base_transform(df, config)
        assert len(out) == len(df)

    def test_filter_before_select(self, df):
        """Column used in filter can be dropped by select."""
        config = TransformConfig(
            column_filters=[ColumnFilter(col="well_id", op="startswith", value="PW")],
            select=["rate"],
        )
        out = apply_base_transform(df, config)
        assert list(out.columns) == ["rate"]
        assert len(out) == 3

    def test_does_not_mutate_input(self, df):
        original_cols = list(df.columns)
        config = TransformConfig(
            renames={"old_name": "new_name"},
            assigns={"extra": 99},
        )
        apply_base_transform(df, config)
        assert list(df.columns) == original_cols


# ---------------------------------------------------------------------------
# From YAML-like dict (model_validate)
# ---------------------------------------------------------------------------

class TestFromDict:
    def test_model_validate_roundtrip(self, df):
        raw = {
            "renames": {"old_name": "new_name"},
            "column_filters": [
                {"col": "well_id", "op": "startswith", "value": "PW"},
                {"col": "rate", "op": "ge", "value": 90.0},
            ],
            "select": ["well_id", "rate", "new_name"],
            "index": "well_id",
        }
        config = TransformConfig.model_validate(raw)
        out = apply_base_transform(df, config)

        assert out.index.name == "well_id"
        assert list(out.columns) == ["rate", "new_name"]
        assert len(out) == 2  # PW001 (120) and PW003 (95)
