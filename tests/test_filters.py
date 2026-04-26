"""
Tests for df_pipeline.filters — build_mask and _get_op_mask.
"""

import pandas as pd
import pytest

from df_pipeline.filters import build_mask, _get_op_mask
from df_pipeline.schema import ColumnFilter


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def flat_df() -> pd.DataFrame:
    return pd.DataFrame({
        "well_id": ["PW001", "PW002", "INJ001", "PW003"],
        "rate":    [120.0,   80.0,    150.0,    95.0],
        "active":  [True,    True,    False,    True],
    })


@pytest.fixture
def multiindex_df() -> pd.DataFrame:
    cols = pd.MultiIndex.from_tuples([
        ("measurement", "temperature"),
        ("measurement", "pressure"),
        ("meta", "well_id"),
    ])
    data = [
        [25.0, 1.2, "PW001"],
        [18.0, 0.9, "PW002"],
        [30.0, 1.5, "INJ001"],
    ]
    return pd.DataFrame(data, columns=cols)


# ---------------------------------------------------------------------------
# _get_op_mask
# ---------------------------------------------------------------------------

class TestGetOpMask:
    def test_ge(self, flat_df):
        mask = _get_op_mask(flat_df["rate"], "ge", 100.0)
        assert mask.tolist() == [True, False, True, False]

    def test_gt(self, flat_df):
        mask = _get_op_mask(flat_df["rate"], "gt", 100.0)
        assert mask.tolist() == [True, False, True, False]

    def test_le(self, flat_df):
        mask = _get_op_mask(flat_df["rate"], "le", 95.0)
        assert mask.tolist() == [False, True, False, True]

    def test_lt(self, flat_df):
        mask = _get_op_mask(flat_df["rate"], "lt", 95.0)
        assert mask.tolist() == [False, True, False, False]

    def test_eq(self, flat_df):
        mask = _get_op_mask(flat_df["rate"], "eq", 80.0)
        assert mask.tolist() == [False, True, False, False]

    def test_ne(self, flat_df):
        mask = _get_op_mask(flat_df["rate"], "ne", 80.0)
        assert mask.tolist() == [True, False, True, True]

    def test_startswith(self, flat_df):
        mask = _get_op_mask(flat_df["well_id"], "startswith", "PW")
        assert mask.tolist() == [True, True, False, True]

    def test_endswith(self, flat_df):
        mask = _get_op_mask(flat_df["well_id"], "endswith", "001")
        assert mask.tolist() == [True, False, True, False]

    def test_contains(self, flat_df):
        mask = _get_op_mask(flat_df["well_id"], "contains", "W0")
        assert mask.tolist() == [True, True, False, True]

    def test_unsupported_op_raises(self, flat_df):
        with pytest.raises(KeyError, match="not supported"):
            _get_op_mask(flat_df["rate"], "modulo", 10)


# ---------------------------------------------------------------------------
# build_mask — flat columns
# ---------------------------------------------------------------------------

class TestBuildMaskFlat:
    def test_empty_filters_returns_all_true(self, flat_df):
        mask = build_mask(flat_df, [])
        assert mask.all()

    def test_single_filter(self, flat_df):
        filters = [ColumnFilter(col="well_id", op="startswith", value="PW")]
        mask = build_mask(flat_df, filters)
        assert mask.tolist() == [True, True, False, True]

    def test_multiple_filters_combined_with_and(self, flat_df):
        filters = [
            ColumnFilter(col="well_id", op="startswith", value="PW"),
            ColumnFilter(col="rate", op="ge", value=90.0),
        ]
        mask = build_mask(flat_df, filters)
        # PW001 (120 >= 90 ✓), PW002 (80 < 90 ✗), INJ001 (not PW ✗), PW003 (95 >= 90 ✓)
        assert mask.tolist() == [True, False, False, True]

    def test_missing_column_raises_keyerror(self, flat_df):
        filters = [ColumnFilter(col="nonexistent", op="eq", value=1)]
        with pytest.raises(KeyError, match="nonexistent"):
            build_mask(flat_df, filters)

    def test_returns_series_aligned_with_index(self, flat_df):
        df = flat_df.set_index("well_id")
        filters = [ColumnFilter(col="rate", op="gt", value=100.0)]
        mask = build_mask(df, filters)
        assert list(mask.index) == list(df.index)


# ---------------------------------------------------------------------------
# build_mask — MultiIndex columns
# ---------------------------------------------------------------------------

class TestBuildMaskMultiIndex:
    def test_multiindex_filter(self, multiindex_df):
        filters = [
            ColumnFilter(col=["measurement", "temperature"], op="ge", value=20.0),
        ]
        mask = build_mask(multiindex_df, filters)
        assert mask.tolist() == [True, False, True]

    def test_multiindex_combined_with_flat_equivalent(self, multiindex_df):
        filters = [
            ColumnFilter(col=["measurement", "temperature"], op="ge", value=20.0),
            ColumnFilter(col=["meta", "well_id"], op="startswith", value="PW"),
        ]
        mask = build_mask(multiindex_df, filters)
        # row 0: temp=25 ✓, well=PW001 ✓ → True
        # row 1: temp=18 ✗                 → False
        # row 2: temp=30 ✓, well=INJ001 ✗ → False
        assert mask.tolist() == [True, False, False]

    def test_multiindex_missing_column_raises(self, multiindex_df):
        filters = [ColumnFilter(col=["measurement", "salinity"], op="ge", value=0)]
        with pytest.raises(KeyError):
            build_mask(multiindex_df, filters)
