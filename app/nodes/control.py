from typing import Dict, Any, List, Tuple
from .base import BaseNode
from ..core.registry import registry
from .utils import parse_bool_strict

@registry.register
class BeginPlay(BaseNode):
    event_node: bool = True
    @classmethod
    def exec_outputs(cls):
        return ["out"]

    @classmethod
    def title(cls):
        return "Begin Play"

    def on_exec(self, **kwargs) -> Tuple[List[str], Dict[str, Any]]:
        return (["out"], {})

@registry.register
class Print(BaseNode):
    @classmethod
    def exec_inputs(cls):
        return ["in"]

    @classmethod
    def exec_outputs(cls):
        return ["then"]

    @classmethod
    def inputs(cls):
        # désormais typé string
        return {"text": str}

    def on_exec(self, text=None, **_) -> Tuple[List[str], Dict[str, Any]]:
        return (["then"], {"printed": text})

@registry.register
class Delay(BaseNode):
    def __init__(self, **params):
        super().__init__(**params)
        self._timer = None
        self._remaining_ms = 0
        self._current_token = None

    @classmethod
    def title(cls):
        return "Delay"

    @classmethod
    def exec_inputs(cls):
        return ["in"]

    @classmethod
    def exec_outputs(cls):
        return ["then"]

    @classmethod
    def inputs(cls):
        # seconds as float
        return {"seconds": float}

    @classmethod
    def category(cls):
        return "Contrôle"

    # Non-réentrant (hérité de BaseNode.reentrant=False)
    def start(self, token_id: int, seconds=None, **_):
        from PyQt5 import QtCore

        # valeur déjà fournie (câble) ou via in_default par le moteur
        if seconds is None:
            QtCore.QTimer.singleShot(
                0,
                lambda tid=token_id: self._scheduler.on_node_finished(self._nid, tid, ["then"], {}),
            )
            return
        try:
            secs = float(str(seconds).replace(",", "."))
        except Exception:
            QtCore.QTimer.singleShot(
                0,
                lambda tid=token_id: self._scheduler.on_node_finished(self._nid, tid, ["then"], {}),
            )
            return

        self._current_token = token_id
        self._remaining_ms = max(0, int(secs * 1000))

        if self._timer:
            self._timer.stop()
            self._timer.deleteLater()

        self._timer = QtCore.QTimer()
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._on_timeout)
        self._timer.start(self._remaining_ms)

    def _on_timeout(self):
        tid = self._current_token
        self._current_token = None
        if self._timer:
            self._timer.deleteLater()
            self._timer = None
        if tid is not None:
            self._scheduler.on_node_finished(self._nid, tid, ["then"], {})

    def cancel(self) -> None:
        if self._timer:
            self._timer.stop()
            self._timer.deleteLater()
            self._timer = None
        self._current_token = None
        self._remaining_ms = 0

    def pause(self) -> None:
        if self._timer and self._timer.isActive():
            self._remaining_ms = self._timer.remainingTime()
            self._timer.stop()

    def resume(self) -> None:
        if self._timer and not self._timer.isActive() and self._current_token is not None:
            self._timer.start(self._remaining_ms)


@registry.register
class Branch(BaseNode):
    @classmethod
    def exec_inputs(cls):
        return ["in"]

    @classmethod
    def exec_outputs(cls):
        return ["true", "false"]

    @classmethod
    def inputs(cls):
        return {"condition": bool}

    def on_exec(self, condition=None, **_):
        b = parse_bool_strict(condition)
        if b is None:
            return ([], {})
        return (["true"] if b else ["false"], {})


@registry.register
class Sequence(BaseNode):
    @classmethod
    def exec_inputs(cls):
        return ["in"]

    @classmethod
    def exec_outputs(cls):
        return ["then1", "then2"]

    def on_exec(self, **_):
        return (["then1", "then2"], {})


@registry.register
class StopExecution(BaseNode):
    """Arrête l'exécution en cours (équivaut au bouton Stop)."""

    @classmethod
    def exec_inputs(cls):
        return ["in"]

    @classmethod
    def exec_outputs(cls):
        return []

    def on_exec(self, **_):
        if getattr(self, "_scheduler", None):
            self._scheduler.cancel_all()
        return ([], {})

# --- Loop nodes (WhileLoop, ForLoop) -----------------------------------
@registry.register
class WhileLoop(BaseNode):
    """While loop with scheduler-driven group idle rechecks.
    - Exec in:  "in"
    - Exec out: "body", "completed"
    - Inputs:   condition: Bool
    Behavior: node stays busy; at each iteration it spawns the body as a group.
    When the group's tokens drain to 0, the scheduler calls back and we re-read
    inputs freshly and decide to iterate again or complete.
    """
    @classmethod
    def title(cls): return "While Loop"

    @classmethod
    def type_name(cls): return "WhileLoop"

    @classmethod
    def exec_inputs(cls): return ["in"]

    @classmethod
    def exec_outputs(cls): return ["body", "completed"]

    @classmethod
    def inputs(cls) -> Dict[str, type]:
        return {"condition": bool}

    def __init__(self, **params):
        super().__init__(**params)
        self._current_token: int | None = None

    # custom start to keep token alive across iterations
    def start(self, token_id: int, **kwargs):
        self._current_token = token_id
        # first decision
        self._recheck()

    def _fresh_kwargs(self) -> Dict[str, Any]:
        # Use scheduler's on-demand recalculation of upstream pure nodes
        if not getattr(self, "_scheduler", None) or not getattr(self, "_nid", None):
            return {}
        return self._scheduler._gather_inputs_live(self._nid)  # type: ignore

    def _recheck(self):
        # Evaluate condition and either spawn the body group or complete
        if self._cond_now():
            self._scheduler.spawn_group(self, "body", on_idle=self._on_body_idle)  # type: ignore
        else:
            self._complete()

    def _cond_now(self) -> bool:
        kw = self._fresh_kwargs()
        val = kw.get("condition", None)
        b = parse_bool_strict(val)
        return bool(b)

    def _on_body_idle(self, _gid: int):
        # One iteration finished → re-evaluate
        if self._cond_now():
            # spawn next iteration
            self._scheduler.spawn_group(self, "body", on_idle=self._on_body_idle)  # type: ignore
        else:
            self._complete()

    def _complete(self):
        tid = self._current_token
        self._current_token = None
        if tid is None:
            return
        # finish with Completed
        self._scheduler.on_node_finished(self._nid, tid, ["completed"], {})  # type: ignore

    def on_exec(self, **kwargs) -> Tuple[List[str], Dict[str, Any]]:
        # Not used when start is overridden, but keep for safety
        if self._cond_now():
            # launch first body iteration
            self._scheduler.spawn_group(self, "body", on_idle=self._on_body_idle)  # type: ignore
            # do not auto-finish here; start() handles lifecycle
            return ([], {})
        else:
            return (["completed"], {})


@registry.register
class ForLoop(BaseNode):
    """For loop (start, end, step, inclusive=false) with group-driven iterations.
    Exposes current index via token data (kwargs) and by updating results dict
    so that data edges from this node's 'index' output are resolved.
    """
    @classmethod
    def title(cls): return "For Loop"

    @classmethod
    def type_name(cls): return "ForLoop"

    @classmethod
    def exec_inputs(cls): return ["in"]

    @classmethod
    def exec_outputs(cls): return ["body", "completed"]

    @classmethod
    def inputs(cls) -> Dict[str, type]:
        return {"start": int, "end": int, "step": int, "inclusive": bool}

    @classmethod
    def outputs(cls) -> Dict[str, type]:
        return {"index": int}

    def __init__(self, **params):
        super().__init__(**params)
        self._current_token: int | None = None
        self._i: int | None = None

    def start(self, token_id: int, **kwargs):
        self._current_token = token_id
        # initialize and go
        kw = self._fresh_kwargs()
        s = int(kw.get("start") if kw.get("start") is not None else self._params.get("in_default:start", self._params.get("start", 0)) or 0)
        e = int(kw.get("end") if kw.get("end") is not None else self._params.get("in_default:end", self._params.get("end", 0)) or 0)
        st = int(kw.get("step") if kw.get("step") is not None else self._params.get("in_default:step", self._params.get("step", 1)) or 1)
        inc = parse_bool_strict(kw.get("inclusive") if kw.get("inclusive") is not None else self._params.get("in_default:inclusive", self._params.get("inclusive", False)))
        self._range = (s, e, st, bool(inc))
        self._i = s
        self._maybe_iter()

    def _fresh_kwargs(self) -> Dict[str, Any]:
        if not getattr(self, "_scheduler", None) or not getattr(self, "_nid", None):
            return {}
        return self._scheduler._gather_inputs_live(self._nid)  # type: ignore

    def _in_range(self, i: int) -> bool:
        s, e, st, inc = self._range
        if st == 0:
            return False
        if st > 0:
            return i <= e if inc else i < e
        else:
            return i >= e if inc else i > e

    def _publish_index(self, i: int):
        # Ensure downstream data edges from this node to 'index' resolve
        prev = self._scheduler.results.get(self._nid, {})  # type: ignore
        prev.update({"index": int(i)})
        self._scheduler.results[self._nid] = prev  # type: ignore

    def _maybe_iter(self):
        i = int(self._i)
        if self._in_range(i):
            self._publish_index(i)
            # spawn body with group; when idle, bump and continue
            self._scheduler.spawn_group(self, "body", on_idle=self._on_body_idle)  # type: ignore
        else:
            self._complete()

    def _on_body_idle(self, _gid: int):
        # bump index and continue
        s, e, st, inc = self._range
        self._i = int(self._i) + st
        self._maybe_iter()

    def _complete(self):
        tid = self._current_token
        self._current_token = None
        if tid is None:
            return
        self._scheduler.on_node_finished(self._nid, tid, ["completed"], {})  # type: ignore
