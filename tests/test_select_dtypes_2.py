# run with: pytest test_validator.py -v
# or as a script: python test_validator.py

import pytest
from pydantic import ValidationError
from df_pipeline.schema import TransformConfig


def test_valid_include():
    cfg = TransformConfig(select_dtypes={"include": "number"})
    assert cfg.select_dtypes == {"include": "number"}


def test_valid_exclude():
    cfg = TransformConfig(select_dtypes={"exclude": "object"})
    assert cfg.select_dtypes == {"exclude": "object"}


def test_unknown_key_rejected():
    with pytest.raises(ValidationError, match="include.*exclude"):
        TransformConfig(select_dtypes={"bad_key": "number"})  # type: ignore[arg-type]


# ── script mode ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    test_valid_include()
    print("ok — include:", TransformConfig(select_dtypes={"include": "number"}).select_dtypes)

    test_valid_exclude()
    print("ok — exclude:", TransformConfig(select_dtypes={"exclude": "object"}).select_dtypes)

    try:
        test_unknown_key_rejected()
        print("FAIL — should have raised")
    except SystemExit:
        pass  # pytest.raises exits in script mode
    finally:
        try:
            TransformConfig(select_dtypes={"bad_key": "number"})  # type: ignore[arg-type]
        except ValidationError as e:
            print("ok — caught:", e.errors()[0]["msg"])