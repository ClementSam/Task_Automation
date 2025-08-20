import types
import app.nodes.variables_runtime as vr
from app.nodes.variables_runtime import SetVariable, GetVariable


def test_set_variable_no_value():
    node = SetVariable(name="var", type="Int")
    engine = types.SimpleNamespace(vars={})
    node._engine = engine
    outs, data = node.on_exec()
    assert outs == ["then"]
    assert data == {}
    assert engine.vars == {}


def test_serial_port_ref_variable(monkeypatch):
    class DummySerialPort:
        pass

    monkeypatch.setattr(vr, "QSerialPort", DummySerialPort)
    dummy = DummySerialPort()

    node = SetVariable(name="port", type="SerialPortRef")
    engine = types.SimpleNamespace(vars={})
    node._engine = engine
    outs, data = node.on_exec(value=dummy)
    assert outs == ["then"]
    assert data == {}
    assert engine.vars["port"] is dummy

    get_node = GetVariable(name="port", type="SerialPortRef")
    get_node._engine = engine
    result = get_node.process()
    assert result["value"] is dummy

    assert vr._cast("not_a_port", "SerialPortRef") is None
