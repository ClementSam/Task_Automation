from typing import Dict, Any
from .base import BaseNode
from ..core.registry import registry

@registry.register
class IntToString(BaseNode):
    @classmethod
    def inputs(cls):
        return {"value": int}
    @classmethod
    def outputs(cls):
        return {"text": str}
    def process(self, value=None, **_) -> Dict[str, Any]:
        try:
            v = int(0 if value is None else value)
        except Exception:
            v = 0
        return {"text": str(v)}

@registry.register
class FloatToString(BaseNode):
    @classmethod
    def inputs(cls):
        return {"value": float}
    @classmethod
    def outputs(cls):
        return {"text": str}
    def process(self, value=None, **_) -> Dict[str, Any]:
        try:
            v = float(0.0 if value is None else value)
        except Exception:
            v = 0.0
        return {"text": str(v)}

@registry.register
class BoolToString(BaseNode):
    @classmethod
    def inputs(cls):
        return {"value": bool}
    @classmethod
    def outputs(cls):
        return {"text": str}
    def process(self, value=None, **_) -> Dict[str, Any]:
        return {"text": "True" if bool(value) else "False"}
