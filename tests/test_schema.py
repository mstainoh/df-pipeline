"""
Tests for df_pipeline.schema — ColumnFilter and TransformConfig validation.
"""

import pytest
from pydantic import ValidationError

from df_pipeline.schema import ColumnFilter, TransformConfig


class TestColumnFilter:
    def test_flat_col(self):
        f = ColumnFilter(col="well_id", op="startswith", value="PW")
        assert f.col_key == "well_id"

    def test_multiindex_col(self):
        f = ColumnFilter(col=["measurement", "temperature"], op="ge", value=20.0)
        assert f.col_key == ("measurement", "temperature")

    def test_value_defaults_to_none(self):
        f = ColumnFilter(col="x", op="eq")
        assert f.value is None

    def test_invalid_op_raises(self):
        with pytest.raises(ValidationError):
            ColumnFilter(col="x", op="modulo", value=1)

    def test_empty_string_col_raises(self):
        with pytest.raises(ValidationError):
            ColumnFilter(col="  ", op="eq", value=1)

    def test_empty_list_col_raises(self):
        with pytest.raises(ValidationError):
            ColumnFilter(col=[], op="eq", value=1)


class TestTransformConfig:
    def test_defaults_are_empty(self):
        config = TransformConfig()
        assert config.renames == {}
        assert config.assigns == {}
        assert config.column_filters == []
        assert config.select is None
        assert config.index is None

    def test_model_validate_from_dict(self):
        raw = {
            "renames": {"a": "b"},
            "column_filters": [{"col": "x", "op": "gt", "value": 0}],
            "index": "b",
        }
        config = TransformConfig.model_validate(raw)
        assert config.renames == {"a": "b"}
        assert len(config.column_filters) == 1
        assert config.index == "b"

    def test_multiindex_filter_in_model_validate(self):
        raw = {
            "column_filters": [
                {"col": ["level1", "level2"], "op": "ge", "value": 5}
            ]
        }
        config = TransformConfig.model_validate(raw)
        assert config.column_filters[0].col_key == ("level1", "level2")

    def test_index_as_list(self):
        config = TransformConfig(index=["a", "b"])
        assert config.index == ["a", "b"]

    def test_null_assigns_value(self):
        config = TransformConfig(assigns={"flag": None})
        assert config.assigns["flag"] is None
