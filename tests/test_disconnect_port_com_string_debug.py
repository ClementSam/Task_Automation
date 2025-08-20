import types
from app.nodes import serial
from app.nodes.serial import DisconnectPortComStringDebug


class DummySerialPort:
    ReadWrite = object()
    open_result = True
    opened = False
    closed = False

    def setPortName(self, name):
        pass

    def open(self, mode):
        DummySerialPort.opened = True
        return self.open_result

    def close(self):
        DummySerialPort.closed = True


def test_disconnect_port_com_string_debug_success(monkeypatch):
    monkeypatch.setattr(serial, "HAVE_SERIAL", True)
    monkeypatch.setattr(serial, "QSerialPort", DummySerialPort)
    DummySerialPort.open_result = True
    DummySerialPort.opened = False
    DummySerialPort.closed = False
    node = DisconnectPortComStringDebug()
    outs, data = node.on_exec(port="COM1")
    assert outs == ["then"]
    assert data["disconnected"] is True
    assert DummySerialPort.opened is True
    assert DummySerialPort.closed is True


def test_disconnect_port_com_string_debug_failure(monkeypatch):
    monkeypatch.setattr(serial, "HAVE_SERIAL", True)
    monkeypatch.setattr(serial, "QSerialPort", DummySerialPort)
    DummySerialPort.open_result = False
    DummySerialPort.opened = False
    DummySerialPort.closed = False
    node = DisconnectPortComStringDebug()
    outs, data = node.on_exec(port="COM1")
    assert outs == ["then"]
    assert data["disconnected"] is False
    assert DummySerialPort.opened is True
    assert DummySerialPort.closed is False


def test_disconnect_port_com_string_debug_missing_port(monkeypatch):
    monkeypatch.setattr(serial, "HAVE_SERIAL", True)
    monkeypatch.setattr(serial, "QSerialPort", DummySerialPort)
    DummySerialPort.open_result = True
    DummySerialPort.opened = False
    DummySerialPort.closed = False
    node = DisconnectPortComStringDebug()
    outs, data = node.on_exec()
    assert outs == ["then"]
    assert data["disconnected"] is False
    assert DummySerialPort.opened is False
