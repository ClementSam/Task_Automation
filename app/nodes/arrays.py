
from typing import Dict, Any, List, Tuple, Optional
from PyQt5 import QtCore
from .base import BaseNode
from ..core.registry import registry
from .variables_runtime import cast_value

# Helpers
_BASE_MAP = { 'String': str, 'Int': int, 'Float': float, 'Bool': bool }

def _base_name(tname: str) -> str:
    # 'Int[]' -> 'Int', 'Float' -> 'Float'
    if isinstance(tname, str) and tname.endswith('[]'):
        return tname[:-2]
    return tname

def _base_dtype(tname: str):
    return _BASE_MAP.get(_base_name(tname), object)

# -------------------- ForEachLoop --------------------
@registry.register
class ForEachLoop(BaseNode):
    """Exécute un corps de boucle pour chaque élément du tableau.
    Ports:
      exec in: 'exec'
      exec out: 'loop', 'completed'
      data in: 'array' (liste typée via param 'type')
      data out: 'element' (scalaire typé), 'index' (int)
    Param:
      type: 'Int[]'|'Float[]'|'String[]'|'Bool[]' (par défaut 'Int[]')
    """

    def __init__(self, **params):
        # defaults for UI
        params = dict({'type': 'Int[]',
                       '_port_types': {'array': tuple, 'element': object, 'index': int},
                       '_port_shapes': {'array': True, 'element': False, 'index': False}}, **params)
        super().__init__(**params)

    @classmethod
    def category(cls): return "Tableaux"
    @classmethod
    def exec_inputs(cls) -> List[str]: return ["exec"]
    @classmethod
    def exec_outputs(cls) -> List[str]: return ["loop", "completed"]
    @classmethod
    def inputs(cls) -> Dict[str, type]: return {"array": object}
    @classmethod
    def outputs(cls) -> Dict[str, type]: return {"element": object, "index": int}

    def start(self, token_id: int, array=None, **kwargs) -> None:
        tname = self._params.get("type", "Int[]")
        arr = cast_value(array, tname)
        if arr is None:
            arr = []
        try:
            total = len(arr)
        except Exception:
            arr = list(arr) if arr is not None else []
            total = len(arr)

        base_t = _base_name(tname)
        # internal iteration state captured by closure
        i = 0
        scheduler = self._scheduler
        nid = self._nid

        def run_next():
            nonlocal i
            # If cancelled/paused handling can be added later
            if i >= total:
                # boucle terminée
                scheduler.on_node_finished(nid, token_id, next_ports=["completed"], out={})
                return
            elem = arr[i]
            # cast element to base type for consistency
            val = cast_value(elem, base_t)
            # expose current element/index as this node's data outputs
            out_map = {"element": val, "index": i}
            # store results so downstream body sees latest element/index
            prev = scheduler.results.get(nid, {})
            prev.update(out_map)
            scheduler.results[nid] = prev
            # lancer le corps ('loop') comme sous-graphe
            def _after(_gid):
                # appel suivant après que le corps soit au repos
                QtCore.QTimer.singleShot(0, run_next)
            scheduler.spawn_group(self, "loop", on_idle=_after)
            i += 1

        # démarrer la première itération (ou terminer si vide)
        QtCore.QTimer.singleShot(0, run_next)

# -------------------- LastIndex --------------------
@registry.register
class LastIndex(BaseNode):
    def __init__(self, **params):
        params = dict({'type': 'Int[]',
                       '_port_types': {'array': tuple, 'index': int},
                       '_port_shapes': {'array': True, 'index': False}}, **params)
        super().__init__(**params)

    @classmethod
    def category(cls): return "Tableaux"
    @classmethod
    def inputs(cls) -> Dict[str, type]: return {"array": object}
    @classmethod
    def outputs(cls) -> Dict[str, type]: return {"index": int}

    def process(self, array=None, **_) -> Dict[str, Any]:
        tname = self._params.get("type", "Int[]")
        arr = cast_value(array, tname)
        try:
            n = len(arr or [])
        except Exception:
            try:
                arr = list(arr) if arr is not None else []
                n = len(arr)
            except Exception:
                n = 0
        return {"index": (n - 1) if n > 0 else -1}

# -------------------- Clear --------------------
@registry.register
class Clear(BaseNode):
    def __init__(self, **params):
        params = dict({'type': 'Int[]',
                       '_port_types': {'array': tuple},
                       '_port_shapes': {'array': True}}, **params)
        super().__init__(**params)

    @classmethod
    def category(cls): return "Tableaux"
    @classmethod
    def inputs(cls) -> Dict[str, type]: return {"array": object}
    @classmethod
    def outputs(cls) -> Dict[str, type]: return {"array": object}

    def process(self, array=None, **_) -> Dict[str, Any]:
        # Always return a new empty list
        return {"array": []}

# -------------------- Add (append) --------------------
@registry.register
class Add(BaseNode):
    def __init__(self, **params):
        params = dict({'type': 'Int[]',
                       '_port_types': {'array': tuple, 'item': object},
                       '_port_shapes': {'array': True, 'item': False}}, **params)
        super().__init__(**params)

    @classmethod
    def category(cls): return "Tableaux"
    @classmethod
    def inputs(cls) -> Dict[str, type]: return {"array": object, "item": object}
    @classmethod
    def outputs(cls) -> Dict[str, type]: return {"array": object}

    def process(self, array=None, item=None, **_) -> Dict[str, Any]:
        tname = self._params.get("type", "Int[]")
        base_t = _base_name(tname)
        arr = cast_value(array, tname)
        if arr is None:
            arr = []
        val = cast_value(item, base_t)
        try:
            out = list(arr)
            out.append(val)
        except Exception:
            try:
                out = list(arr or [])
                out.append(val)
            except Exception:
                out = arr or []
        return {"array": out}

# -------------------- Find --------------------
@registry.register
class Find(BaseNode):
    def __init__(self, **params):
        params = dict({'type': 'Int[]',
                       'case_sensitive': True,
                       '_port_types': {'array': tuple, 'item': object, 'index': int},
                       '_port_shapes': {'array': True, 'item': False, 'index': False}}, **params)
        super().__init__(**params)

    @classmethod
    def category(cls): return "Tableaux"
    @classmethod
    def inputs(cls) -> Dict[str, type]: return {"array": object, "item": object}
    @classmethod
    def outputs(cls) -> Dict[str, type]: return {"index": int}

    def process(self, array=None, item=None, **_) -> Dict[str, Any]:
        tname = self._params.get("type", "Int[]")
        base_t = _base_name(tname)
        arr = cast_value(array, tname) or []
        needle = cast_value(item, base_t)

        # Handle case-insensitive search for strings
        if base_t == "String" and not bool(self._params.get("case_sensitive", True)):
            try:
                target = (needle or "").lower()
                for i, it in enumerate(arr):
                    if (it or "").lower() == target:
                        return {"index": i}
                return {"index": -1}
            except Exception:
                return {"index": -1}

        # Default equality
        try:
            for i, it in enumerate(arr):
                if it == needle:
                    return {"index": i}
            return {"index": -1}
        except Exception:
            return {"index": -1}
