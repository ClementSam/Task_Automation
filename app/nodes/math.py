from typing import Dict, Any
from .base import BaseNode
from ..core.registry import registry

@registry.register
class ConstantNumber(BaseNode):

    @classmethod
    def category(cls):
        return "Math"
    @classmethod
    def outputs(cls):
        return {"value": float}

    @classmethod
    def title(cls):
        return "Constant (float)"

    def process(self, **kwargs) -> Dict[str, Any]:
        v = self.params().get("value", 0.0)
        try:
            v = float(v)
        except Exception:
            v = 0.0
        return {"value": v}

@registry.register
class ConstantInt(BaseNode):

    @classmethod
    def category(cls):
        return "Math"
    @classmethod
    def outputs(cls):
        return {"value": int}

    @classmethod
    def title(cls):
        return "Constant (int)"

    def process(self, **kwargs) -> Dict[str, Any]:
        v = self.params().get("value", 0)
        try:
            v = int(v)
        except Exception:
            v = 0
        return {"value": v}

@registry.register
class ConstantBool(BaseNode):

    @classmethod
    def category(cls):
        return "Math"
    @classmethod
    def outputs(cls):
        return {"value": bool}

    @classmethod
    def title(cls):
        return "Constant (bool)"

    def process(self, **kwargs) -> Dict[str, Any]:
        v = self.params().get("value", False)
        return {"value": bool(v)}

@registry.register
class Add(BaseNode):

    @classmethod
    def category(cls):
        return "Math"
    @classmethod
    def inputs(cls):
        return {"a": float, "b": float}

    @classmethod
    def outputs(cls):
        return {"sum": float}

    def process(self, a=None, b=None, **_) -> Dict[str, Any]:
        a = 0.0 if a is None else float(a)
        b = 0.0 if b is None else float(b)
        return {"sum": a + b}

@registry.register
class Multiply(BaseNode):

    @classmethod
    def category(cls):
        return "Math"
    @classmethod
    def inputs(cls):
        return {"a": float, "b": float}

    @classmethod
    def outputs(cls):
        return {"product": float}

    def process(self, a=None, b=None, **_) -> Dict[str, Any]:
        a = 0.0 if a is None else float(a)
        b = 0.0 if b is None else float(b)
        return {"product": a * b}
