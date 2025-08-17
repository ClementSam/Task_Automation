from typing import Dict, Any, List, Tuple
from .base import BaseNode
from ..core.registry import registry

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

        # Parse seconds robustement (accepte "1,23")
        try:
            if seconds is None:
                secs = 0.0
            elif isinstance(seconds, str):
                secs = float(seconds.replace(",", "."))
            else:
                secs = float(seconds)
        except Exception:
            secs = 0.0

        msecs = max(0, int(secs * 1000))

        # Timer sans lifetime à gérer → pas de GC aléatoire
        QtCore.QTimer.singleShot(
            msecs,
            lambda tid=token_id: self._scheduler.on_node_finished(self._nid, tid, ["then"], {})
        )

