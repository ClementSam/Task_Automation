
from typing import Dict, Any, List, Tuple, Optional
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
class WaitSerialMessage(BaseNode, QtCore.QObject):
    """Non-blocking wait for a line on a serial port."""

    reentrant: bool = False
    event_node: bool = True  # color as event

    def __init__(self, **params):
        QtCore.QObject.__init__(self)
        BaseNode.__init__(self, **params)
        self._serial: Optional[QSerialPort] = None
        self._buffer = bytearray()
        self._timer: Optional[QtCore.QTimer] = None
        self._current_token: Optional[int] = None

    @classmethod
    def title(cls): return "Wait Serial Message"
    @classmethod
    def type_name(cls): return "WaitSerialMessage"
    @classmethod
    def inputs(cls): return {"port": str, "baud": int}
    @classmethod
    def outputs(cls): return {"text": str}
    @classmethod
    def exec_outputs(cls) -> List[str]: return ["then"]

    def _ensure_open(self, port: str, baud: int) -> bool:
        if not HAVE_SERIAL: raise RuntimeError("QtSerialPort manquant (PyQt5.QtSerialPort).")
        if self._serial and self._serial.isOpen():
            if self._serial.portName()==port and self._serial.baudRate()==baud: return True
            self._serial.close()
        self._serial = QSerialPort(); self._serial.setPortName(port); self._serial.setBaudRate(baud or 115200)
        ok = self._serial.open(QSerialPort.ReadOnly)
        if ok: self._serial.readyRead.connect(self._on_ready)
        return ok

    def _on_ready(self):
        if not self._serial:
            return
        self._buffer.extend(self._serial.readAll().data())
        if b"\n" in self._buffer:
            line, _, rest = self._buffer.partition(b"\n")
            self._buffer = bytearray(rest)
            text = line.decode(errors="replace").rstrip("\r")
            self._finish(text)

    def _on_timeout(self):
        self._finish("")

    def _finish(self, text: str):
        if self._serial:
            try:
                self._serial.readyRead.disconnect(self._on_ready)
            except Exception:
                pass
            try:
                self._serial.close()
            except Exception:
                pass
        if self._timer:
            self._timer.stop()
            self._timer.deleteLater()
            self._timer = None
        token = self._current_token
        self._current_token = None
        QtCore.QTimer.singleShot(
            0,
            lambda: self._scheduler.on_node_finished(
                self._nid, token, ["then"], {"text": text}
            ),
        )

    def start(self, token_id: int, port=None, baud=None, **_):
        if self._current_token is not None:
            # shouldn't happen due to scheduler single-seat, but guard
            self.enqueue_local(token_id)
            return
        port = port or self._params.get("port") or "COM3"
        baud = baud or self._params.get("baud") or 115200
        if not self._ensure_open(port, baud):
            QtCore.QTimer.singleShot(
                0,
                lambda: self._scheduler.on_node_finished(
                    self._nid, token_id, ["then"], {"text": ""}
                ),
            )
            return
        self._current_token = token_id
        self._buffer.clear()
        timeout_ms = int(self._params.get("timeout", 3000))
        self._timer = QtCore.QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._on_timeout)
        self._timer.start(timeout_ms)

    def cancel(self) -> None:
        self._finish("")
