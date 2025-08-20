import types
from app.nodes.variables_runtime import SetVariable


def test_set_variable_no_value():
    node = SetVariable(name="var", type="Int")
    engine = types.SimpleNamespace(vars={})
    node._engine = engine
    outs, data = node.on_exec()
    assert outs == ["then"]
    assert data == {}
    assert engine.vars == {}
