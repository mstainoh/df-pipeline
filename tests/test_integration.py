"""
Integration tests for apply_base_transform.

Covers the full pipeline from CSV + YAML through to a validated output
DataFrame, including a custom-registered transform op (m3h_to_ls).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest
import yaml

# Make sure src/ is on the path when running from repo root
sys.path.insert(0, str(Path(__file__).parent.parent))

# ---------------------------------------------------------------------------
# Register custom ops BEFORE any TransformConfig is instantiated
# ---------------------------------------------------------------------------
import examples.custom_transforms as custom_transforms
custom_transforms.register_all()

from df_pipeline import apply_base_transform
from df_pipeline.schema import TransformConfig, ColumnTransform


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

BASE = Path(__file__).parent.parent


@pytest.fixture
def raw_df() -> pd.DataFrame:
    df = pd.read_csv(BASE / "examples/data/test_data_1.csv")
    df.columns = df.columns.str.strip()   # CSV has leading/trailing spaces in header
    return df


@pytest.fixture
def config() -> TransformConfig:
    params = yaml.safe_load((BASE / "examples/config/test_data_1.yaml").read_text())
    return TransformConfig.model_validate(params["transform"]["data"])


@pytest.fixture
def result(raw_df, config) -> pd.DataFrame:
    return apply_base_transform(raw_df, config)


# ---------------------------------------------------------------------------
# Structure tests
# ---------------------------------------------------------------------------

def test_index_is_node_id(result):
    assert result.index.name == "node_id"


def test_expected_columns(result):
    expected = {"group", "flow_rate_m3h", "flow_rate_ls", "duration_days", "data_source"}
    assert expected == set(result.columns)


def test_data_source_assigned(result):
    assert (result["data_source"] == "test_data_1").all()


# ---------------------------------------------------------------------------
# Filter tests
# ---------------------------------------------------------------------------

def test_only_group_A(result):
    assert (result["group"] == "A").all()


def test_flow_rate_gt_13(result):
    assert (result["flow_rate_m3h"] > 13.0).all()


# ---------------------------------------------------------------------------
# Column transform tests
# ---------------------------------------------------------------------------

def test_m3h_to_ls_conversion(result):
    """flow_rate_ls must equal flow_rate_m3h / 3.6."""
    expected = result["flow_rate_m3h"] / 3.6
    pd.testing.assert_series_equal(
        result["flow_rate_ls"],
        expected,
        check_names=False,
    )


def test_duration_days_positive(result):
    """end_date > start_date in all test rows — diff must be positive."""
    assert (result["duration_days"] > 0).all()


# ---------------------------------------------------------------------------
# Custom op registration test
# ---------------------------------------------------------------------------

def test_custom_op_registered():
    """unit_convert must be accepted by ColumnTransform after register_all()."""
    ct = ColumnTransform(col="flow_rate_m3h", op="unit_convert", dest="flow_rate_ls")
    assert ct.op == "unit_convert"


def test_unregistered_op_raises():
    """Unknown op must raise ValueError at ColumnTransform construction."""
    with pytest.raises(ValueError, match="not registered"):
        ColumnTransform(col="x", op="nonexistent_op", dest="y")
