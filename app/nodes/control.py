from typing import Dict, Any, List, Tuple
from .base import BaseNode
from ..core.registry import registry

@registry.register
class BeginPlay(BaseNode):
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
