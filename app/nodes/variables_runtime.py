
from typing import Dict, Any, List, Tuple
from .base import BaseNode
from ..core.registry import registry
from .utils import parse_bool_strict
from .scope_types import ScopeRef

try:
    from PyQt5.QtSerialPort import QSerialPort
except Exception:  # pragma: no cover - optional dependency
    QSerialPort = object

_TYPE_MAP = { 'String': str, 'Int': int, 'Float': float, 'Bool': bool }

def _decompose_type(tname: str):
    if isinstance(tname, str) and tname.endswith('[]'):
        return tname[:-2], True
    return tname, False

def _split_items(s: str) -> list:
    s = (s or '').strip()
    if not s:
        return []
    if s.startswith('[') and s.endswith(']'):
        s = s[1:-1]
    return [p.strip() for p in s.split(',') if p.strip() != '']

def cast_value(val, tname: str):
    base_t, is_array = _decompose_type(tname)
    if not is_array:
        return _cast(val, base_t)
    if val is None or val == '':
        return []
    if isinstance(val, str):
        items = _split_items(val)
    elif isinstance(val, (list, tuple)):
        items = list(val)
    else:
        items = [val]
    return [_cast(x, base_t) for x in items]


def _cast(val, tname: str):
    if tname == 'ScopeRef':
        return val if val is None or isinstance(val, ScopeRef) else None
    if tname == 'SerialPortRef':
        return val if val is None or isinstance(val, QSerialPort) else None
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
        return {"value": cast_value(eng.vars.get(name), tname)}

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

        val = cast_value(raw, tname)
        eng.vars[name] = val
        return (["then"], {})
