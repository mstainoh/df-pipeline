
"""
Tests for df_pipeline.transforms — apply_base_transform pipeline.
"""

import pandas as pd
from pydantic import ValidationError
import pytest

from df_pipeline.schema import ColumnTransform
from df_pipeline.transforms import apply_column_transforms


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


class TestColArithmetic:
    @pytest.fixture
    def df(self):
        return pd.DataFrame({"a": [10.0, 20.0], "b": [2.0, 4.0]})

    # ------------------------------------------------------------------
    # Individual ops
    # ------------------------------------------------------------------
    @pytest.mark.parametrize("op,expected", [
        ("col_add", [12.0, 24.0]),
        ("col_sub", [ 8.0, 16.0]),
        ("col_mul", [20.0, 80.0]),
        ("col_div", [ 5.0,  5.0]),
    ])
    def test_individual_ops(self, df, op, expected):
        ct = ColumnTransform(col="a", other_col="b", op=op, dest="result")
        out = apply_column_transforms(df, [ct])
        pd.testing.assert_series_equal(
            out["result"],
            pd.Series(expected, name="result"),
        )

    # ------------------------------------------------------------------
    # col_arithmetic — valid ops
    # ------------------------------------------------------------------
    @pytest.mark.parametrize("op,expected", [
        ("mul", [20.0, 80.0]),
        ("add", [12.0, 24.0]),
        ("sub", [ 8.0, 16.0]),
        ("pow", [100.0, 160000.0]),   # 10**2, 20**4
        ("mod", [ 0.0,  0.0]),        # 10%2, 20%4
    ])
    def test_col_arithmetic_valid_ops(self, df, op, expected):
        ct = ColumnTransform(
            col="a", other_col="b",
            op="col_arithmetic", dest="result",
            params={"op": op},
        )
        out = apply_column_transforms(df, [ct])
        pd.testing.assert_series_equal(
            out["result"],
            pd.Series(expected, name="result"),
        )

    def test_col_arithmetic_invalid_op_raises(self, df):
        ct = ColumnTransform(
            col="a", other_col="b",
            op="col_arithmetic", dest="result",
            params={"op": "div"},   # div no está en ArithmeticValidOperator
        )
        with pytest.raises(ValueError, match="Unrecognized operator"):
            apply_column_transforms(df, [ct])

    # ------------------------------------------------------------------
    # requires_other_col enforced by Pydantic
    # ------------------------------------------------------------------
    def test_col_add_without_other_col_raises(self):
        with pytest.raises(ValidationError):
            ColumnTransform(col="a", op="col_add", dest="result")

    # ------------------------------------------------------------------
    # dest overwrites col when omitted
    # ------------------------------------------------------------------
    def test_col_mul_overwrites_col_when_no_dest(self, df):
        ct = ColumnTransform(col="a", other_col="b", op="col_mul")
        out = apply_column_transforms(df, [ct])
        pd.testing.assert_series_equal(
            out["a"],
            pd.Series([20.0, 80.0], name="a"),
        )