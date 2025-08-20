from typing import Dict, Any
from .base import BaseNode
from ..core.registry import registry
from .utils import parse_bool_strict


@registry.register
class ConstInt(BaseNode):
    CATEGORY = "Variables"
    COLOR = "#E06C75"

    @classmethod
    def title(cls) -> str:
        return "Const Int"

    @classmethod
    def type_name(cls) -> str:
        return "ConstInt"

    @classmethod
    def outputs(cls) -> Dict[str, type]:
        return {"value": int}

    def process(self, **kwargs) -> Dict[str, Any]:
        raw = self._params.get("value", None)
        if raw in (None, ""):
            return {"value": None}
        try:
            return {"value": int(raw)}
        except Exception:
            return {"value": None}


@registry.register
class ConstFloat(BaseNode):
    CATEGORY = "Variables"
    COLOR = "#2BB1FF"

    @classmethod
    def title(cls) -> str:
        return "Const Float"

    @classmethod
    def type_name(cls) -> str:
        return "ConstFloat"

    @classmethod
    def outputs(cls) -> Dict[str, type]:
        return {"value": float}

    def process(self, **kwargs) -> Dict[str, Any]:
        raw = self._params.get("value", None)
        if raw in (None, ""):
            return {"value": None}
        try:
            return {"value": float(raw)}
        except Exception:
            return {"value": None}


@registry.register
class ConstBool(BaseNode):
    CATEGORY = "Variables"
    COLOR = "#98C379"

    @classmethod
    def title(cls) -> str:
        return "Const Bool"

    @classmethod
    def type_name(cls) -> str:
        return "ConstBool"

    @classmethod
    def outputs(cls) -> Dict[str, type]:
        return {"value": bool}

    def process(self, **kwargs) -> Dict[str, Any]:
        b = parse_bool_strict(self._params.get("value", None))
        return {"value": b}


@registry.register
class ConstString(BaseNode):
    CATEGORY = "Variables"
    COLOR = "#C678DD"

    @classmethod
    def title(cls) -> str:
        return "Const String"

    @classmethod
    def type_name(cls) -> str:
        return "ConstString"

    @classmethod
    def outputs(cls) -> Dict[str, type]:
        return {"value": str}

    def process(self, **kwargs) -> Dict[str, Any]:
        raw = self._params.get("value", None)
        if raw in (None, ""):
            return {"value": None}
        try:
            return {"value": str(raw)}
        except Exception:
            return {"value": None}
