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



@registry.register
class StringToBool(BaseNode):
    @classmethod
    def category(cls):
        return "Conversion"
    @classmethod
    def inputs(cls):
        return {"text": str}
    @classmethod
    def outputs(cls):
        return {"value": bool}
    def process(self, text=None, **_) -> Dict[str, Any]:
        b = parse_bool_strict(text)
        return {"value": b}

@registry.register
class StringToFloat(BaseNode):
    @classmethod
    def category(cls):
        return "Conversion"
    @classmethod
    def inputs(cls):
        return {"text": str}
    @classmethod
    def outputs(cls):
        return {"value": float}
    def process(self, text=None, **_) -> Dict[str, Any]:
        if text in (None, ""):
            return {"value": None}
        try:
            return {"value": float(text)}
        except Exception:
            return {"value": None}

@registry.register
class StringToInt(BaseNode):
    @classmethod
    def category(cls):
        return "Conversion"
    @classmethod
    def inputs(cls):
        return {"text": str}
    @classmethod
    def outputs(cls):
        return {"value": int}
    def process(self, text=None, **_) -> Dict[str, Any]:
        if text in (None, ""):
            return {"value": None}
        try:
            return {"value": int(text)}
        except Exception:
            return {"value": None}

@registry.register
class FloatToInt(BaseNode):
    @classmethod
    def category(cls):
        return "Conversion"
    @classmethod
    def inputs(cls):
        return {"value": float}
    @classmethod
    def outputs(cls):
        return {"value": int}
    def process(self, value=None, **_) -> Dict[str, Any]:
        if value is None:
            return {"value": None}
        try:
            return {"value": int(float(value))}
        except Exception:
            return {"value": None}

@registry.register
class IntToFloat(BaseNode):
    @classmethod
    def category(cls):
        return "Conversion"
    @classmethod
    def inputs(cls):
        return {"value": int}
    @classmethod
    def outputs(cls):
        return {"value": float}
    def process(self, value=None, **_) -> Dict[str, Any]:
        if value is None:
            return {"value": None}
        try:
            return {"value": float(value)}
        except Exception:
            return {"value": None}
