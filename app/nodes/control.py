from typing import Dict, Any, List, Tuple
from .base import BaseNode
from ..core.registry import registry
from .utils import parse_bool_strict

@registry.register
class BeginPlay(BaseNode):
    event_node: bool = True
    @classmethod
    def exec_outputs(cls):
        return ["out"]

    @classmethod
    def title(cls):
        return "Begin Play"

    def on_exec(self, **kwargs) -> Tuple[List[str], Dict[str, Any]]:
        return (["out"], {})

@registry.register
class Print(BaseNode):
    @classmethod
    def exec_inputs(cls):
        return ["in"]

    @classmethod
    def exec_outputs(cls):
        return ["then"]

    @classmethod
    def inputs(cls):
        # désormais typé string
        return {"text": str}

    def on_exec(self, text=None, **_) -> Tuple[List[str], Dict[str, Any]]:
        return (["then"], {"printed": text})

@registry.register
class Delay(BaseNode):
    def __init__(self, **params):
        super().__init__(**params)
        self._timer = None
        self._remaining_ms = 0
        self._current_token = None

    @classmethod
    def title(cls):
        return "Delay"

    @classmethod
    def exec_inputs(cls):
        return ["in"]

    @classmethod
    def exec_outputs(cls):
        return ["then"]

    @classmethod
    def inputs(cls):
        # seconds as float
        return {"seconds": float}

    @classmethod
    def category(cls):
        return "Contrôle"

    # Non-réentrant (hérité de BaseNode.reentrant=False)
    def start(self, token_id: int, seconds=None, **_):
        from PyQt5 import QtCore

        # valeur déjà fournie (câble) ou via in_default par le moteur
        if seconds is None:
            QtCore.QTimer.singleShot(
                0,
                lambda tid=token_id: self._scheduler.on_node_finished(self._nid, tid, ["then"], {}),
            )
            return
        try:
            secs = float(str(seconds).replace(",", "."))
        except Exception:
            QtCore.QTimer.singleShot(
                0,
                lambda tid=token_id: self._scheduler.on_node_finished(self._nid, tid, ["then"], {}),
            )
            return

        self._current_token = token_id
        self._remaining_ms = max(0, int(secs * 1000))

        if self._timer:
            self._timer.stop()
            self._timer.deleteLater()

        self._timer = QtCore.QTimer()
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._on_timeout)
        self._timer.start(self._remaining_ms)

    def _on_timeout(self):
        tid = self._current_token
        self._current_token = None
        if self._timer:
            self._timer.deleteLater()
            self._timer = None
        if tid is not None:
            self._scheduler.on_node_finished(self._nid, tid, ["then"], {})

    def cancel(self) -> None:
        if self._timer:
            self._timer.stop()
            self._timer.deleteLater()
            self._timer = None
        self._current_token = None
        self._remaining_ms = 0

    def pause(self) -> None:
        if self._timer and self._timer.isActive():
            self._remaining_ms = self._timer.remainingTime()
            self._timer.stop()

    def resume(self) -> None:
        if self._timer and not self._timer.isActive() and self._current_token is not None:
            self._timer.start(self._remaining_ms)


@registry.register
class Branch(BaseNode):
    @classmethod
    def exec_inputs(cls):
        return ["in"]

    @classmethod
    def exec_outputs(cls):
        return ["true", "false"]

    @classmethod
    def inputs(cls):
        return {"condition": bool}

    def on_exec(self, condition=None, **_):
        b = parse_bool_strict(condition)
        if b is None:
            return ([], {})
        return (["true"] if b else ["false"], {})


@registry.register
class Sequence(BaseNode):
    @classmethod
    def exec_inputs(cls):
        return ["in"]

    @classmethod
    def exec_outputs(cls):
        return ["then1", "then2"]

    def on_exec(self, **_):
        return (["then1", "then2"], {})

