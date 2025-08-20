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
        if a is None or b is None:
            return {"equal": None}
        return {"equal": str(a) == str(b)}

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
        if a is None or b is None:
            return {"text": None}
        return {"text": str(a) + str(b)}
