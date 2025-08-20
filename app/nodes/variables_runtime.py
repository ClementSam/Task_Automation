
from typing import Dict, Any, List, Tuple
from .base import BaseNode
from ..core.registry import registry
from .utils import parse_bool_strict

_TYPE_MAP = { 'String': str, 'Int': int, 'Float': float, 'Bool': bool }

def _cast(val, tname: str):
    typ = _TYPE_MAP.get(tname, str)
    if val is None:
        return None
    if typ is bool:
        return parse_bool_strict(val)
    try:
        return typ(val)
    except Exception:
        return None

@registry.register
class GetVariable(BaseNode):
    HIDDEN = True
    @classmethod
    def title(cls): return "Get Variable"
    @classmethod
    def type_name(cls): return "GetVariable"
    @classmethod
    def outputs(cls): return {"value": object}
    @classmethod
    def inputs(cls): return {}

    def process(self, **kwargs) -> Dict[str, Any]:
        eng = getattr(self, "_engine", None)
        if not eng: raise RuntimeError("Engine indisponible.")
        name = self._params.get("name", "")
        tname = self._params.get("type", "String")
        return {"value": _cast(eng.vars.get(name), tname)}

@registry.register
class SetVariable(BaseNode):
    HIDDEN = True
    @classmethod
    def title(cls): return "Set Variable"
    @classmethod
    def type_name(cls): return "SetVariable"
    @classmethod
    def inputs(cls): return {"value": object}
    @classmethod
    def exec_inputs(cls): return ["in"]
    @classmethod
    def exec_outputs(cls): return ["then"]

    def on_exec(self, **kwargs) -> Tuple[List[str], Dict[str, Any]]:
        eng = getattr(self, "_engine", None)
        if not eng: raise RuntimeError("Engine indisponible.")
        name  = self._params.get("name", "")
        tname = self._params.get("type", "String")

        raw = kwargs.get("value", None)
        if raw is None:
            raw = self._params.get("in_default:value", self._params.get("value"))

        if raw is None:  # pas de câble et pas de champ -> ne rien écrire
            return (["then"], {})

        val = _cast(raw, tname)
        eng.vars[name] = val
        return (["then"], {})
