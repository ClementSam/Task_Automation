import types
from app.nodes import serial
from app.nodes.serial import ConnectPortCom


class DummySerialPort:
    ReadWrite = object()
    open_result = True
    dtr = None

    def setPortName(self, name):
        pass

    def setBaudRate(self, baud):
        pass

    def open(self, mode):
        return self.open_result

    def setDataTerminalReady(self, value):
        self.dtr = value


def test_connect_port_com_success(monkeypatch):
    monkeypatch.setattr(serial, "HAVE_SERIAL", True)
    monkeypatch.setattr(serial, "QSerialPort", DummySerialPort)
    serial.QSerialPort.open_result = True
    node = ConnectPortCom()
    outs, data = node.on_exec(port="COM1", baud=9600)
    assert outs == ["then"]
    assert isinstance(data["serial_port"], serial.QSerialPort)
    assert data["connected"] is True
    assert data["serial_port"].dtr is True


def test_connect_port_com_failure(monkeypatch):
    monkeypatch.setattr(serial, "HAVE_SERIAL", True)
    monkeypatch.setattr(serial, "QSerialPort", DummySerialPort)
    serial.QSerialPort.open_result = False
    node = ConnectPortCom()
    outs, data = node.on_exec(port="COM1", baud=9600)
    assert outs == ["then"]
    assert data["serial_port"] is None
    assert data["connected"] is False


def test_connect_port_com_disable_dtr(monkeypatch):
    monkeypatch.setattr(serial, "HAVE_SERIAL", True)
    monkeypatch.setattr(serial, "QSerialPort", DummySerialPort)
    serial.QSerialPort.open_result = True
    node = ConnectPortCom()
    outs, data = node.on_exec(port="COM1", baud=9600, dtr=False)
    assert outs == ["then"]
    assert isinstance(data["serial_port"], serial.QSerialPort)
    assert data["connected"] is True
    assert data["serial_port"].dtr is False
