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

    def on_exec(self, seconds=None, **_) -> Tuple[List[str], Dict[str, Any]]:
        try:
            secs = float(0.0 if seconds is None else seconds)
        except Exception:
            secs = 0.0
        # Non-blocking-ish wait to keep UI responsive
        try:
            from PyQt5.QtCore import QCoreApplication
            import time as _t
            end = _t.monotonic() + max(0.0, secs)
            while _t.monotonic() < end:
                QCoreApplication.processEvents()
                _t.sleep(0.01)
        except Exception:
            import time as _t
            _t.sleep(max(0.0, secs))
        return (["then"], {})
