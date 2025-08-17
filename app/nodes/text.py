from typing import Dict, Any
from .base import BaseNode
from ..core.registry import registry

@registry.register
class IsEgalText(BaseNode):
    @classmethod
    def category(cls):
        return "Text"

    @classmethod
    def inputs(cls):
        return {"a": str, "b": str}

    @classmethod
    def outputs(cls):
        return {"equal": bool}

    def process(self, a=None, b=None, **_) -> Dict[str, Any]:
        a = "" if a is None else str(a)
        b = "" if b is None else str(b)
        return {"equal": a == b}

@registry.register
class AppendText(BaseNode):
    @classmethod
    def category(cls):
        return "Text"

    @classmethod
    def inputs(cls):
        return {"a": str, "b": str}

    @classmethod
    def outputs(cls):
        return {"text": str}

    def process(self, a=None, b=None, **_) -> Dict[str, Any]:
        a = "" if a is None else str(a)
        b = "" if b is None else str(b)
        return {"text": a + b}
