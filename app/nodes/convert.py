from typing import Dict, Any
from .base import BaseNode
from ..core.registry import registry
from .utils import parse_bool_strict

@registry.register
class IntToString(BaseNode):

    @classmethod
    def category(cls):
        return "Conversion"
    @classmethod
    def inputs(cls):
        return {"value": int}
    @classmethod
    def outputs(cls):
        return {"text": str}
    def process(self, value=None, **_) -> Dict[str, Any]:
        if value is None:
            return {"text": None}
        try:
            return {"text": str(int(value))}
        except Exception:
            return {"text": None}

@registry.register
class FloatToString(BaseNode):

    @classmethod
    def category(cls):
        return "Conversion"
    @classmethod
    def inputs(cls):
        return {"value": float}
    @classmethod
    def outputs(cls):
        return {"text": str}
    def process(self, value=None, **_) -> Dict[str, Any]:
        if value is None:
            return {"text": None}
        try:
            return {"text": str(float(value))}
        except Exception:
            return {"text": None}

@registry.register
class BoolToString(BaseNode):

    @classmethod
    def category(cls):
        return "Conversion"
    @classmethod
    def inputs(cls):
        return {"value": bool}
    @classmethod
    def outputs(cls):
        return {"text": str}
    def process(self, value=None, **_) -> Dict[str, Any]:
        b = parse_bool_strict(value)
        if b is None:
            return {"text": None}
        return {"text": "True" if b else "False"}
