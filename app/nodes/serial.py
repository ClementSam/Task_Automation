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
    def outputs(cls):
        return {"serial_port": QSerialPort, "connected": bool}

    def on_exec(self, port=None, baud=None, **_):
        if not HAVE_SERIAL:
            raise RuntimeError("QtSerialPort manquant (PyQt5.QtSerialPort).")
        port = port or self._params.get("port") or "COM3"
        baud = baud or self._params.get("baud") or 115200
        ser = QSerialPort()
        ser.setPortName(str(port))
        ser.setBaudRate(int(baud) or 115200)
        ok = ser.open(QSerialPort.ReadWrite)
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
            try:
                msg = text or ""
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

    def __init__(self, **params):
        # default state for enabled input is True
        params.setdefault("in_default:enabled", True)
        QtCore.QObject.__init__(self)
        BaseNode.__init__(self, **params)
        self._serial: Optional[QSerialPort] = None
        self._buffer = bytearray()
        self._active = False  # phantom token state

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

    # ----- internal helpers -----
    def _activate(self, serial_port: QSerialPort) -> None:
        self._serial = serial_port
        self._buffer.clear()
        self._serial.readyRead.connect(self._on_ready)
        self._serial.errorOccurred.connect(self._on_error)
        self._active = True
        hooks = getattr(self._scheduler, "hooks", None)
        if hooks and hasattr(hooks, "on_node_start"):
            try:
                hooks.on_node_start(self._nid)
            except Exception:
                pass

    def _deactivate(self) -> None:
        if self._serial:
            try:
                self._serial.readyRead.disconnect(self._on_ready)
            except Exception:
                pass
            try:
                self._serial.errorOccurred.disconnect(self._on_error)
            except Exception:
                pass
        self._serial = None
        self._buffer.clear()
        if self._active:
            hooks = getattr(self._scheduler, "hooks", None)
            if hooks and hasattr(hooks, "on_node_finish"):
                try:
                    hooks.on_node_finish(self._nid)
                except Exception:
                    pass
        self._active = False

    # ----- serial callbacks -----
    def _on_ready(self):
        if not (self._serial and self._active):
            return
        self._buffer.extend(self._serial.readAll().data())
        while b"\n" in self._buffer:
            line, _, rest = self._buffer.partition(b"\n")
            self._buffer = bytearray(rest)
            text = line.decode(errors="replace").rstrip("\r")
            self._emit_message(text)

    def _on_error(self, *_):
        self._deactivate()

    def _emit_message(self, text: str) -> None:
        sched = self._scheduler
        if not sched:
            return
        prev = sched.results.get(self._nid, {})
        prev.update({"text": text})
        sched.results[self._nid] = prev
        hooks = getattr(sched, "hooks", None)
        if hooks and hasattr(hooks, "on_node_output"):
            try:
                hooks.on_node_output(self._nid, {"text": text})
            except Exception:
                pass
        for dst_id, dst_port in sched.exec_outgoing.get((self._nid, "exec_on_message"), []):
            if hooks and hasattr(hooks, "on_edge_fired"):
                try:
                    hooks.on_edge_fired(self._nid, "exec_on_message", dst_id, dst_port)
                except Exception:
                    pass
            child = sched._new_token(dst_id, {})
            sched.post_ready(child)

    # ----- execution entry -----
    def start(self, token_id: int, serial_port: Optional[QSerialPort] = None, enabled=True, **_):
        QtCore.QTimer.singleShot(
            0,
            lambda tid=token_id: self._scheduler.on_node_finished(
                self._nid, tid, ["exec_out_pass"], {}
            ),
        )
        if self._active:
            self._deactivate()
        if enabled and HAVE_SERIAL and isinstance(serial_port, QSerialPort) and serial_port.isOpen():
            self._activate(serial_port)

    def cancel(self) -> None:  # pragma: no cover - defensive cleanup
        self._deactivate()

