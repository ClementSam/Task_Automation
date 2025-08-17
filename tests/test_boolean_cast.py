import pytest
from app.nodes.variables_runtime import _cast

@pytest.mark.parametrize("input_val, expected", [
    ("True", True),
    ("true", True),
    ("False", False),
    ("false", False),
    ("1", True),
    ("0", False),
    ("yes", True),
    ("no", False),
    (True, True),
    (False, False),
])
def test_cast_bool(input_val, expected):
    assert _cast(input_val, "Bool") == expected
