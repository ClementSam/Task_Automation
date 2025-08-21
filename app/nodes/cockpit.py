
from typing import Dict, Any
from PyQt5 import QtCore
from .base import BaseNode
from ..core.registry import registry
from .utils import parse_bool_strict

@registry.register
class SetLed(BaseNode):
    @classmethod
    def category(cls): return "Cockpit"
    @classmethod
    def title(cls): return "SetLed"
    @classmethod
    def exec_inputs(cls): return ["in"]
    @classmethod
    def exec_outputs(cls): return ["then"]
    @classmethod
    def inputs(cls): return {"target": str, "on": bool, "color": str}
    @classmethod
    def outputs(cls): return {}

    def on_exec(self, target=None, on=None, color=None, **_) -> tuple[list[str], dict]:
        if target is None:
            target = self._params.get("in_default:target", self._params.get("target"))
        if on is None:
            on = self._params.get("in_default:on", self._params.get("on"))
        if color is None:
            color = self._params.get("in_default:color", self._params.get("color"))
        b = parse_bool_strict(on)
        if target is None or b is None:
            return (["then"], {})
        if hasattr(self._scheduler, "on_cockpit_led_set"):
            try:
                self._scheduler.on_cockpit_led_set.emit(str(target), bool(b), color)
            except Exception:
                pass
        return (["then"], {})

@registry.register
class WriteText(BaseNode):
    @classmethod
    def category(cls): return "Cockpit"
    @classmethod
    def title(cls): return "WriteText"
    @classmethod
    def exec_inputs(cls): return ["in"]
    @classmethod
    def exec_outputs(cls): return ["then"]
    @classmethod
    def inputs(cls): return {"target": str, "text": str, "mode": str, "newline": bool}
    @classmethod
    def outputs(cls): return {}

    def on_exec(self, target=None, text=None, mode=None, newline=None, **_) -> tuple[list[str], dict]:
        if target is None:
            target = self._params.get("in_default:target", self._params.get("target"))
        if text is None:
            text = self._params.get("in_default:text", self._params.get("text"))
        if mode is None:
            mode = self._params.get("in_default:mode", self._params.get("mode"))
        if newline is None:
            newline = self._params.get("in_default:newline", self._params.get("newline"))
        b_newline = parse_bool_strict(newline) or False
        m = (mode or "").strip().lower() if isinstance(mode, str) else None
        if target is None:
            return (["then"], {})
        clear = (m == "clear")
        append = (m == "append")
        payload = text if (text is not None) else ""
        if append and b_newline and isinstance(payload, str):
            payload = payload + "\n"
        if hasattr(self._scheduler, "on_cockpit_text_set"):
            try:
                self._scheduler.on_cockpit_text_set.emit(str(target), payload, bool(clear), bool(append))
            except Exception:
                pass
        try:
            if clear:
                self._scheduler.set_cockpit_text_cache(str(target), "")
            elif append:
                prev = self._scheduler.ui_cockpit_get_text(str(target)) or ""
                self._scheduler.set_cockpit_text_cache(str(target), str(prev) + str(payload))
            else:
                self._scheduler.set_cockpit_text_cache(str(target), "" if payload is None else str(payload))
        except Exception:
            pass
        return (["then"], {})

@registry.register
class ReadText(BaseNode):
    @classmethod
    def category(cls): return "Cockpit"
    @classmethod
    def title(cls): return "ReadText"
    @classmethod
    def inputs(cls): return {"target": str}
    @classmethod
    def outputs(cls): return {"text": str}

    def process(self, target=None, **_) -> Dict[str, Any]:
        if target is None:
            target = self._params.get("in_default:target", self._params.get("target"))
        if target is None:
            return {"text": None}
        try:
            v = self._scheduler.ui_cockpit_get_text(str(target))
        except Exception:
            v = None
        return {"text": v}

@registry.register
class OnCockpitButton(BaseNode, QtCore.QObject):
    reentrant: bool = False
    event_node: bool = True
    is_event_source = True

    @classmethod
    def category(cls): return "Cockpit"
    @classmethod
    def title(cls): return "OnCockpitButton"
    @classmethod
    def exec_inputs(cls): return ["exec_in"]
    @classmethod
    def exec_outputs(cls): return ["exec_out_pass", "exec_on_press"]
    @classmethod
    def inputs(cls): return {"target": str, "enabled": bool}
    @classmethod
    def outputs(cls): return {}

    def __init__(self, **params):
        QtCore.QObject.__init__(self)
        BaseNode.__init__(self, **params)
        self._listening = False
        self._sub_connected = False
        self._target: str | None = None

    def _ui_listening(self, on: bool) -> None:
        if hasattr(self._engine, "ui_node_set_listening"):
            self._engine.ui_node_set_listening(self._nid, on)

    def _on_button(self, btn_id: str):
        if not self._listening:
            return
        if self._target and str(btn_id) != str(self._target):
            return
        sched = self._scheduler
        if not sched:
            return
        child = sched._new_token(self._nid, {"clicked": True})
        sched.post_ready(child)

    def _subscribe(self):
        if self._sub_connected or not hasattr(self._scheduler, "on_cockpit_button_clicked"):
            return
        try:
            self._scheduler.on_cockpit_button_clicked.connect(self._on_button)
            self._sub_connected = True
        except Exception:
            pass

    def _unsubscribe(self):
        if self._sub_connected and hasattr(self._scheduler, "on_cockpit_button_clicked"):
            try:
                self._scheduler.on_cockpit_button_clicked.disconnect(self._on_button)
            except Exception:
                pass
        self._sub_connected = False

    def pause(self):
        self._unsubscribe()

    def resume(self):
        if self._listening:
            self._subscribe()

    def cancel(self):
        self._ui_listening(False)
        self._unsubscribe()

    def start(self, token_id: int = None, target=None, enabled=None, clicked=None, **_):
        if clicked:
            QtCore.QTimer.singleShot(
                0,
                lambda tid=token_id: self._scheduler.on_node_finished(
                    self._nid, tid, ["exec_on_press"], {}
                ),
            )
            return

        if target is None:
            target = self._params.get("in_default:target", self._params.get("target"))
        if enabled is None:
            enabled = self._params.get("in_default:enabled", self._params.get("enabled"))
        b = parse_bool_strict(enabled)
        if b is None:
            QtCore.QTimer.singleShot(
                0,
                lambda tid=token_id: self._scheduler.on_node_finished(
                    self._nid, tid, ["exec_out_pass"], {}
                ),
            )
            return

        self._target = str(target) if target is not None else None
        self._listening = bool(b)
        self._ui_listening(self._listening)
        if self._listening:
            self._subscribe()
        else:
            self._unsubscribe()

        QtCore.QTimer.singleShot(
            0,
            lambda tid=token_id: self._scheduler.on_node_finished(
                self._nid, tid, ["exec_out_pass"], {}
            ),
        )
