from typing import Dict, Any
from .base import BaseNode
from ..core.registry import registry
from .utils import parse_bool_strict

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
        raw = self.params().get("value", None)
        if raw in (None, ""):
            return {"value": None}
        try:
            return {"value": float(raw)}
        except Exception:
            return {"value": None}

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
        raw = self.params().get("value", None)
        if raw in (None, ""):
            return {"value": None}
        try:
            return {"value": int(raw)}
        except Exception:
            return {"value": None}

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
        b = parse_bool_strict(self.params().get("value", None))
        return {"value": b}

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
        if a is None or b is None:
            return {"sum": None}
        try:
            return {"sum": float(a) + float(b)}
        except Exception:
            return {"sum": None}

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
        if a is None or b is None:
            return {"product": None}
        try:
            return {"product": float(a) * float(b)}
        except Exception:
            return {"product": None}
