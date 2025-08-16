from typing import Dict, Any
from .base import BaseNode
from ..core.registry import registry


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
        val = self._params.get("value", 0)
        try:
            val = int(val)
        except Exception:
            val = 0
        return {"value": val}


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
        val = self._params.get("value", 0.0)
        try:
            val = float(val)
        except Exception:
            val = 0.0
        return {"value": val}


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
        return {"value": bool(self._params.get("value", False))}


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
        return {"value": str(self._params.get("value", ""))}
