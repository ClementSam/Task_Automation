from typing import Dict, Any
from .base import BaseNode
from ..core.registry import registry
from .utils import parse_bool_strict




@registry.register
class Add_Float(BaseNode):

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
class Multiply_Float(BaseNode):

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



@registry.register
class Add_Int(BaseNode):
    @classmethod
    def category(cls):
        return "Math"
    @classmethod
    def inputs(cls):
        return {"a": int, "b": int}
    @classmethod
    def outputs(cls):
        return {"sum": int}
    def process(self, a=None, b=None, **_) -> Dict[str, Any]:
        if a is None or b is None:
            return {"sum": None}
        try:
            return {"sum": int(a) + int(b)}
        except Exception:
            return {"sum": None}

@registry.register
class Multiply_Int(BaseNode):
    @classmethod
    def category(cls):
        return "Math"
    @classmethod
    def inputs(cls):
        return {"a": int, "b": int}
    @classmethod
    def outputs(cls):
        return {"product": int}
    def process(self, a=None, b=None, **_) -> Dict[str, Any]:
        if a is None or b is None:
            return {"product": None}
        try:
            return {"product": int(a) * int(b)}
        except Exception:
            return {"product": None}
