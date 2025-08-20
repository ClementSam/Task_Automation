from typing import List, Optional
from PyQt5 import QtCore
try:
    from PyQt5.QtSerialPort import QSerialPort
    HAVE_SERIAL = True
except Exception:
    QSerialPort = None
    HAVE_SERIAL = False

from .base import BaseNode
from ..core.registry import registry
from .utils import parse_bool_strict


@registry.register
class ConnectPortCom(BaseNode):
    @classmethod
    def title(cls): return "Connect Port Com"

    @classmethod
    def type_name(cls): return "ConnectPortCom"

    @classmethod
    def exec_inputs(cls): return ["in"]

    @classmethod
    def exec_outputs(cls): return ["then"]

    @classmethod
    def inputs(cls):
        return {"port": str, "baud": int, "dtr": bool}

    @classmethod
    def outputs(cls):
        return {"serial_port": QSerialPort, "connected": bool}

    def on_exec(self, port=None, baud=None, dtr=None, **_):
        if not HAVE_SERIAL:
            raise RuntimeError("QtSerialPort manquant (PyQt5.QtSerialPort).")

        if port is None:
            port = self._params.get("in_default:port", self._params.get("port"))
        if baud is None:
            baud = self._params.get("in_default:baud", self._params.get("baud"))
        if dtr is None:
            dtr = self._params.get("in_default:dtr", self._params.get("dtr"))

        if port in (None, "") or baud in (None, ""):
            return (["then"], {"serial_port": None, "connected": False})

        ser = QSerialPort()
        ser.setPortName(str(port))
        try:
            ser.setBaudRate(int(baud))
        except Exception:
            return (["then"], {"serial_port": None, "connected": False})

        ok = ser.open(QSerialPort.ReadWrite)
        if ok:
            b = parse_bool_strict(dtr)
            if b is not None:
                try:
                    ser.setDataTerminalReady(b)
                except Exception:
                    pass
        return (["then"], {"serial_port": ser if ok else None, "connected": ok})


@registry.register
class DisconnectPortCom(BaseNode):
    @classmethod
    def title(cls): return "Disconnect Port Com"

    @classmethod
    def type_name(cls): return "DisconnectPortCom"

    @classmethod
    def exec_inputs(cls): return ["in"]

    @classmethod
    def exec_outputs(cls): return ["then"]

    @classmethod
    def inputs(cls): return {"serial_port": QSerialPort}

    def on_exec(self, serial_port=None, **_):
        if HAVE_SERIAL and isinstance(serial_port, QSerialPort):
            try:
                serial_port.close()
            except Exception:
                pass
        return (["then"], {})


@registry.register
class DisconnectPortComStringDebug(BaseNode):
    @classmethod
    def title(cls): return "Disconnect Port Com (Debug)"

    @classmethod
    def type_name(cls): return "DisconnectPortComStringDebug"

    @classmethod
    def exec_inputs(cls): return ["in"]

    @classmethod
    def exec_outputs(cls): return ["then"]

    @classmethod
    def inputs(cls): return {"port": str}

    @classmethod
    def outputs(cls): return {"disconnected": bool}

    def on_exec(self, port=None, **_):
        if not HAVE_SERIAL:
            raise RuntimeError("QtSerialPort manquant (PyQt5.QtSerialPort).")
        if port is None:
            port = self._params.get("in_default:port", self._params.get("port"))
        if port in (None, ""):
            return (["then"], {"disconnected": False})
        ser = QSerialPort()
        ser.setPortName(str(port))
        ok = False
        try:
            ok = ser.open(QSerialPort.ReadWrite)
            if ok:
                ser.close()
        except Exception:
            ok = False
        return (["then"], {"disconnected": ok})


@registry.register
class IsValid(BaseNode):
    @classmethod
    def title(cls):
        return "Is Valid"

    @classmethod
    def type_name(cls):
        return "IsValid"

    @classmethod
    def exec_inputs(cls) -> List[str]:
        return ["in"]

    @classmethod
    def exec_outputs(cls) -> List[str]:
        return ["valid", "invalid"]

    @classmethod
    def inputs(cls):
        return {"serial_port": QSerialPort}

    def on_exec(self, serial_port=None, **_):
        port = "valid" if serial_port else "invalid"
        return ([port], {})


@registry.register
class SendPortComMessage(BaseNode):
    @classmethod
    def title(cls): return "Send Port Com Message"

    @classmethod
    def type_name(cls): return "SendPortComMessage"

    @classmethod
    def exec_inputs(cls): return ["in"]

    @classmethod
    def exec_outputs(cls): return ["then"]

    @classmethod
    def inputs(cls): return {"serial_port": QSerialPort, "text": str}

    def on_exec(self, serial_port=None, text=None, **_):
        if HAVE_SERIAL and isinstance(serial_port, QSerialPort) and serial_port.isOpen():
            msg = text
            if msg is None:
                msg = self._params.get("in_default:text", self._params.get("text"))
            if msg in (None, ""):
                return (["then"], {})
            try:
                if not msg.endswith("\n"):
                    msg += "\n"
                data = msg.encode("utf-8")
                serial_port.write(data)
                try:
                    serial_port.waitForBytesWritten(50)
                except Exception:
                    pass
            except Exception:
                pass
        return (["then"], {})


@registry.register
class OnPortComMessage(BaseNode, QtCore.QObject):
    """Listen to a serial port and emit an execution for each received line."""

    reentrant: bool = False
    event_node: bool = True
    is_event_source = True

    def __init__(self, **params):
        QtCore.QObject.__init__(self)
        BaseNode.__init__(self, **params)
        self._serial: Optional[QSerialPort] = None
        self._buffer = bytearray()
        self._listening = False

    @classmethod
    def title(cls):
        return "On Port Com Message"

    @classmethod
    def type_name(cls):
        return "OnPortComMessage"

    @classmethod
    def inputs(cls):
        return {"serial_port": QSerialPort, "enabled": bool}

    @classmethod
    def outputs(cls):
        return {"text": str}

    @classmethod
    def exec_inputs(cls) -> List[str]:
        return ["exec_in"]

    @classmethod
    def exec_outputs(cls) -> List[str]:
        return ["exec_out_pass", "exec_on_message"]

    def _open_port_if_needed(self, serial_port: QSerialPort) -> None:
        self._serial = serial_port
        self._buffer.clear()

    def _close_port_if_needed(self) -> None:
        self._serial = None
        self._buffer.clear()

    def _subscribe_serial(self) -> None:
        if self._serial:
            try:
                self._serial.readyRead.connect(self._on_ready)
            except Exception:
                pass
            try:
                self._serial.errorOccurred.connect(self._on_error)
            except Exception:
                pass

    def _unsubscribe_serial(self) -> None:
        if self._serial:
            try:
                self._serial.readyRead.disconnect(self._on_ready)
            except Exception:
                pass
            try:
                self._serial.errorOccurred.disconnect(self._on_error)
            except Exception:
                pass

    def _suspend_serial_listener(self, pause: bool) -> None:
        if pause:
            self._unsubscribe_serial()
        else:
            self._subscribe_serial()

    def _ui_listening(self, on: bool) -> None:
        if hasattr(self._engine, "ui_node_set_listening"):
            self._engine.ui_node_set_listening(self._nid, on)

    def _on_ready(self):
        if not (self._serial and self._listening):
            return
        self._buffer.extend(self._serial.readAll().data())
        while b"\n" in self._buffer:
            line, _, rest = self._buffer.partition(b"\n")
            self._buffer = bytearray(rest)
            text = line.decode(errors="replace").rstrip("\r")
            self._on_serial_msg(text)

    def _on_error(self, *_):
        self._unsubscribe_serial()

    def _on_serial_msg(self, payload: str):
        sched = self._scheduler
        if not sched:
            return
        child = sched._new_token(self._nid, {"message": payload})
        sched.post_ready(child)

    def start(self, token_id: int = None, serial_port: Optional[QSerialPort] = None, enabled=None, message: str = None, **_):
        if message is not None:
            QtCore.QTimer.singleShot(
                0,
                lambda tid=token_id, msg=message: self._scheduler.on_node_finished(
                    self._nid, tid, ["exec_on_message"], {"text": msg}
                ),
            )
            return

        QtCore.QTimer.singleShot(
            0,
            lambda tid=token_id: self._scheduler.on_node_finished(
                self._nid, tid, ["exec_out_pass"], {}
            ),
        )

        self._listening = bool(enabled)
        self._ui_listening(self._listening)
        if self._listening and HAVE_SERIAL and isinstance(serial_port, QSerialPort) and serial_port.isOpen():
            self._open_port_if_needed(serial_port)
            self._subscribe_serial()
        else:
            self._unsubscribe_serial()
            self._close_port_if_needed()

    def pause(self):
        self._suspend_serial_listener(True)

    def resume(self):
        if self._listening:
            self._suspend_serial_listener(False)

    def cancel(self):  # pragma: no cover - defensive cleanup
        self._ui_listening(False)
        self._unsubscribe_serial()
        self._close_port_if_needed()
