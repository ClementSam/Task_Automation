
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
    reentrant: bool = False
    event_node: bool = True  # color as event
    def __init__(self, **params):
        QtCore.QObject.__init__(self); BaseNode.__init__(self, **params)
        self._serial: Optional[QSerialPort] = None
        self._buffer = bytearray()

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
        if not self._serial: return
        self._buffer.extend(self._serial.readAll().data())
        if b"\n" in self._buffer:
            line, _, rest = self._buffer.partition(b"\n"); self._buffer = bytearray(rest)
            self._last_text = line.decode(errors="replace").rstrip("\r")
            if self._loop and self._loop.isRunning():
                self._serial.close()
                self._loop.quit()

    def on_exec(self, **kwargs) -> Tuple[List[str], Dict[str, Any]]:
        port = kwargs.get("port") or self._params.get("port") or "COM3"
        baud = kwargs.get("baud") or self._params.get("baud") or 115200
        if not self._ensure_open(port, baud): raise RuntimeError(f"Impossible d'ouvrir {port}")
        self._last_text = ""
        self._loop = QtCore.QEventLoop()
        self._loop.exec_()  # no timeout by design
        return (["then"], {"text": self._last_text})
