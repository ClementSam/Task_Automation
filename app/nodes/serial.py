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
    def inputs(cls): return {"port": str, "baud": int}

    @classmethod
    def outputs(cls): return {"handle": object}

    def on_exec(self, port=None, baud=None, **_):
        if not HAVE_SERIAL:
            raise RuntimeError("QtSerialPort manquant (PyQt5.QtSerialPort).")
        port = port or self._params.get("port") or "COM3"
        baud = baud or self._params.get("baud") or 115200
        ser = QSerialPort()
        ser.setPortName(str(port))
        ser.setBaudRate(int(baud) or 115200)
        ok = ser.open(QSerialPort.ReadWrite)
        return (["then"], {"handle": ser if ok else None})


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
    def inputs(cls): return {"handle": object}

    def on_exec(self, handle=None, **_):
        if HAVE_SERIAL and isinstance(handle, QSerialPort):
            try:
                handle.close()
            except Exception:
                pass
        return (["then"], {})


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
    def inputs(cls): return {"handle": object, "text": str}

    def on_exec(self, handle=None, text=None, **_):
        if HAVE_SERIAL and isinstance(handle, QSerialPort) and handle.isOpen():
            data = (text or "").encode()
            try:
                handle.write(data)
            except Exception:
                pass
        return (["then"], {})


@registry.register
class OnPortComMessage(BaseNode, QtCore.QObject):
    reentrant: bool = False
    event_node: bool = True

    def __init__(self, **params):
        QtCore.QObject.__init__(self)
        BaseNode.__init__(self, **params)
        self._serial: Optional[QSerialPort] = None
        self._buffer = bytearray()
        self._timer: Optional[QtCore.QTimer] = None
        self._current_token: Optional[int] = None

    @classmethod
    def title(cls): return "On Port Com Message"

    @classmethod
    def type_name(cls): return "OnPortComMessage"

    @classmethod
    def inputs(cls): return {"handle": object}

    @classmethod
    def outputs(cls): return {"text": str}

    @classmethod
    def exec_inputs(cls): return ["in"]

    @classmethod
    def exec_outputs(cls) -> List[str]: return ["then"]

    def _on_ready(self):
        if not self._serial:
            return
        self._buffer.extend(self._serial.readAll().data())
        if b"\n" in self._buffer:
            line, _, rest = self._buffer.partition(b"\n")
            self._buffer = bytearray(rest)
            text = line.decode(errors="replace").rstrip("\r")
            self._finish(text)

    def _on_error(self, *_):
        self._finish("")

    def _on_timeout(self):
        self._finish("")

    def _finish(self, text: str):
        if self._serial:
            try:
                self._serial.readyRead.disconnect(self._on_ready)
            except Exception:
                pass
            try:
                self._serial.errorOccurred.disconnect(self._on_error)
            except Exception:
                pass
        if self._timer:
            self._timer.stop()
            self._timer.deleteLater()
            self._timer = None
        token = self._current_token
        self._current_token = None
        self._serial = None
        QtCore.QTimer.singleShot(
            0,
            lambda: self._scheduler.on_node_finished(
                self._nid, token, ["then"], {"text": text}
            ),
        )

    def start(self, token_id: int, handle=None, **_):
        if self._current_token is not None:
            self.enqueue_local(token_id)
            return
        if not (HAVE_SERIAL and isinstance(handle, QSerialPort) and handle.isOpen()):
            QtCore.QTimer.singleShot(
                0,
                lambda tid=token_id: self._scheduler.on_node_finished(
                    self._nid, tid, ["then"], {"text": ""}
                ),
            )
            return
        self._current_token = token_id
        self._serial = handle
        self._buffer.clear()
        self._serial.readyRead.connect(self._on_ready)
        self._serial.errorOccurred.connect(self._on_error)
        timeout_ms = int(self._params.get("timeout", 3000))
        self._timer = QtCore.QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._on_timeout)
        self._timer.start(timeout_ms)

    def cancel(self) -> None:
        self._finish("")

