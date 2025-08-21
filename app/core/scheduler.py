from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Any, Optional, Tuple, Deque
from collections import deque, defaultdict
from PyQt5 import QtCore

from .engine import DEFAULT_PREFIX, NodeSpec, EdgeSpec
from .registry import registry


@dataclass
class Token:
    id: int
    target: str
    data: Dict[str, Any]
    cancelled: bool = False
    gid: int | None = None


class Scheduler(QtCore.QObject):
    """Single-threaded scheduler driving node execution."""

    sigRunFinished = QtCore.pyqtSignal(dict)
    on_state_changed = QtCore.pyqtSignal(str)
    on_active_tokens_changed = QtCore.pyqtSignal(int)
    on_token_started = QtCore.pyqtSignal(str, int)
    on_token_finished = QtCore.pyqtSignal(str, int)
    on_reset_node_visuals = QtCore.pyqtSignal()
    on_node_listening_changed = QtCore.pyqtSignal(str, bool)
    # Cockpit signals
    on_cockpit_led_set = QtCore.pyqtSignal(str, bool, object)
    on_cockpit_text_set = QtCore.pyqtSignal(str, object, bool, bool)
    on_cockpit_button_clicked = QtCore.pyqtSignal(str)

    def __init__(self, parent=None, hooks: Optional[object] = None):
        super().__init__(parent)
        self.hooks = hooks
        self._continuous_run: bool = False
        self._active_tokens: int = 0
        self._ready: Deque[int] = deque()
        self.nodes: Dict[str, Any] = {}
        self.tokens: Dict[int, Token] = {}
        self.results: Dict[str, Dict[str, Any]] = {}
        self.vars: Dict[str, Any] = {}
        self.data_incoming: Dict[Tuple[str, str], Tuple[str, str]] = {}
        self.exec_outgoing: Dict[Tuple[str, str], List[Tuple[str, str]]] = defaultdict(list)
        self._next_token = 1
        self._draining = False
        self._pure_nodes: List[str] = []
        self._exec_nodes: List[str] = []
        self._paused = False
        # cockpit text cache (for ReadText)
        self._cockpit_text_cache: Dict[str, str] = {}
        # group execution tracking for loop bodies
        self._group_active: Dict[int, int] = {}
        self._group_on_idle: Dict[int, list] = {}
        self._next_gid: int = 1


    # ---- configuration -------------------------------------------------
    def set_continuous_run(self, enabled: bool) -> None:
        self._continuous_run = bool(enabled)
        self._emit_state()

    def is_continuous_run(self) -> bool:
        return self._continuous_run

    # ---- graph setup --------------------------------------------------
    def setup(self, nodes: List[NodeSpec], edges: List[EdgeSpec], vars_init: Dict[str, Any]):
        self._ready.clear()
        self.tokens.clear()
        self.results.clear()
        self.vars = dict(vars_init or {})
        self.data_incoming.clear()
        self.exec_outgoing.clear()
        self.nodes.clear()
        self._pure_nodes.clear()
        self._exec_nodes.clear()
        self._next_token = 1
        self._active_tokens = 0
        self._paused = False
        # cockpit text cache (for ReadText)
        self._cockpit_text_cache: Dict[str, str] = {}
        # group execution tracking for loop bodies
        self._group_active: Dict[int, int] = {}
        self._group_on_idle: Dict[int, list] = {}
        self._next_gid: int = 1


        for spec in nodes:
            inst = registry.create(spec.type_name, **spec.params)
            inst.attach(self, spec.id)
            setattr(inst, "_engine", self)  # for variable nodes
            self.nodes[spec.id] = inst
        for e in edges:
            if e.kind == "data":
                self.data_incoming[(e.dst_id, e.dst_port)] = (e.src_id, e.src_port)
            else:
                self.exec_outgoing[(e.src_id, e.src_port)].append((e.dst_id, e.dst_port))
        for nid, inst in self.nodes.items():
            if inst.exec_inputs() or inst.exec_outputs():
                self._exec_nodes.append(nid)
            else:
                self._pure_nodes.append(nid)

    # ---- data helpers --------------------------------------------------
    def _build_data_graph(self, only_nodes: List[str]):
        adj = {nid: [] for nid in only_nodes}
        indeg = {nid: 0 for nid in only_nodes}
        for (dst_id, dst_port), (src_id, src_port) in self.data_incoming.items():
            if dst_id in indeg and src_id in indeg:
                adj[src_id].append(dst_id)
                indeg[dst_id] += 1
        return adj, indeg

    def _topological_order_subset(self, subset: List[str]) -> List[str]:
        adj, indeg = self._build_data_graph(subset)
        q = [nid for nid in subset if indeg[nid] == 0]
        order = []
        while q:
            nid = q.pop(0)
            order.append(nid)
            for nxt in adj[nid]:
                indeg[nxt] -= 1
                if indeg[nxt] == 0:
                    q.append(nxt)
        return order

    def _gather_inputs(self, nid: str) -> Dict[str, Any]:
        node = self.nodes[nid]
        params = node.params()
        kwargs = {}
        for in_name in node.inputs().keys():
            if (nid, in_name) in self.data_incoming:
                src_id, src_port = self.data_incoming[(nid, in_name)]
                kwargs[in_name] = self.results.get(src_id, {}).get(src_port)
            else:
                key = DEFAULT_PREFIX + in_name
                kwargs[in_name] = params.get(key, None)
        return kwargs

    # New helpers for on-demand evaluation of upstream pure nodes
    def _collect_upstream_pure(self, nid: str) -> List[str]:
        """Return list of upstream pure node ids for ``nid``.

        Traverses data inputs recursively while the source node is pure
        (i.e. has no exec inputs/outputs). Traversal stops when reaching
        an exec node.
        """
        pure = set(self._pure_nodes)
        seen = set()
        result = set()
        stack: List[str] = [nid]
        incoming = self.data_incoming
        while stack:
            dst = stack.pop()
            for (d_id, d_port), (s_id, s_port) in incoming.items():
                if d_id != dst:
                    continue
                if s_id in seen:
                    continue
                seen.add(s_id)
                if s_id in pure:
                    result.add(s_id)
                    stack.append(s_id)
        return list(result)

    def _gather_inputs_with_memo(self, nid: str, memo: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """Gather inputs for ``nid`` prioritising memoised results."""
        node = self.nodes[nid]
        params = node.params()
        kwargs: Dict[str, Any] = {}
        for in_name in node.inputs().keys():
            key = (nid, in_name)
            if key in self.data_incoming:
                src_id, src_port = self.data_incoming[key]
                src_map = memo.get(src_id, self.results.get(src_id, {}))
                kwargs[in_name] = src_map.get(src_port)
            else:
                dkey = DEFAULT_PREFIX + in_name
                kwargs[in_name] = params.get(dkey, None)
        return kwargs

    def _gather_inputs_live(self, nid: str) -> Dict[str, Any]:
        """Recalculate upstream pure nodes for ``nid`` and gather kwargs."""
        subset = self._collect_upstream_pure(nid)
        memo: Dict[str, Dict[str, Any]] = {}
        if subset:
            order = self._topological_order_subset(subset)
            for dnid in order:
                dnode = self.nodes[dnid]
                dkwargs = self._gather_inputs_with_memo(dnid, memo)
                dout = dnode.process(**dkwargs) or {}
                memo[dnid] = dout
                self.results[dnid] = dout
        return self._gather_inputs_with_memo(nid, memo)

    def ui_node_set_listening(self, nid: str, on: bool) -> None:
        self.on_node_listening_changed.emit(nid, bool(on))

    # ---- token helpers -------------------------------------------------
    def _new_token(self, nid: str, data: Optional[Dict[str, Any]] = None, *, gid: int | None = None) -> int:
        tid = self._next_token
        self._next_token += 1
        tok = Token(tid, nid, data or {})
        tok.gid = gid
        self.tokens[tid] = tok
        self._inc_active(1)
        if gid is not None:
            self._group_active[gid] = self._group_active.get(gid, 0) + 1
        return tid

    def post_ready(self, tid: int) -> None:
        was_empty = not self._ready
        self._ready.append(tid)
        if was_empty:
            self._emit_state("running")
        if not self._paused:
            QtCore.QTimer.singleShot(0, self.drain)

    # ---- running -------------------------------------------------------
    def start_run(self):
        # entry nodes have no exec inputs
        entry_nodes = [nid for nid in self._exec_nodes if not self.nodes[nid].exec_inputs()]
        for nid in entry_nodes:
            tid = self._new_token(nid, {})
            self.post_ready(tid)

    def drain(self):
        if self._draining or self._paused:
            return
        self._draining = True
        try:
            while self._ready:
                tid = self._ready.popleft()
                tok = self.tokens.get(tid)
                if not tok or tok.cancelled:
                    continue
                nid = tok.target
                node = self.nodes[nid]
                if node.busy:
                    node.enqueue_local(tid)
                    continue
                node.busy = True
                self.on_token_started.emit(nid, tid)
                if self.hooks and hasattr(self.hooks, "on_node_start"):
                    try:
                        self.hooks.on_node_start(nid)
                    except Exception:
                        pass
                kwargs = self._gather_inputs_live(nid)
                kwargs.update(tok.data)
                node.start(tid, **kwargs)
        finally:
            self._draining = False

    # called by nodes when finished
    def on_node_finished(self, nid: str, tid: int, next_ports: Optional[List[str]], out: Optional[Dict[str, Any]]):
        node = self.nodes[nid]
        # capture token and group id
        tok = self.tokens.get(tid)
        parent_gid = tok.gid if tok is not None else None

        # mark node idle and remove token
        node.busy = False
        self.tokens.pop(tid, None)
        self._inc_active(-1)

        # group accounting (defer idle notification until after child propagation)
        if parent_gid is not None:
            self._group_active[parent_gid] = max(0, self._group_active.get(parent_gid, 0) - 1)

        # record outputs and fire hooks
        self.on_token_finished.emit(nid, tid)
        prev = self.results.get(nid, {}) or {}
        prev.update(out or {})
        self.results[nid] = prev
        if self.hooks and hasattr(self.hooks, "on_node_output"):
            try:
                self.hooks.on_node_output(nid, out or {})
            except Exception:
                pass
        if self.hooks and hasattr(self.hooks, "on_node_finish"):
            try:
                self.hooks.on_node_finish(nid)
            except Exception:
                pass

        # start next token from local queue if any (same node)
        nxt = node.dequeue_local()
        if nxt is not None:
            node.busy = True
            self.on_token_started.emit(nid, nxt)
            if self.hooks and hasattr(self.hooks, "on_node_start"):
                try:
                    self.hooks.on_node_start(nid)
                except Exception:
                    pass
            kwargs = self._gather_inputs_live(nid)
            kwargs.update(self.tokens[nxt].data)
            node.start(nxt, **kwargs)

        # propagate exec edges, inheriting gid
        for port in next_ports or []:
            for (dst_id, dst_port) in self.exec_outgoing.get((nid, port), []):
                if self.hooks and hasattr(self.hooks, "on_edge_fired"):
                    try:
                        self.hooks.on_edge_fired(nid, port, dst_id, dst_port)
                    except Exception:
                        pass
                child = self._new_token(dst_id, {}, gid=parent_gid)
                self.post_ready(child)

        # after propagation, if group is empty, notify idle
        if parent_gid is not None and self._group_active.get(parent_gid, 0) == 0:
            self._notify_group_idle(parent_gid)

        self._maybe_finish()

    # cancellation -------------------------------------------------------
    def cancel_all(self) -> None:
        for tok in self.tokens.values():
            tok.cancelled = True
        for node in self.nodes.values():
            try:
                node.cancel()
            except Exception:
                pass
        self.tokens.clear()
        self._ready.clear()
        self._active_tokens = 0
        self._group_active.clear()
        self._group_on_idle.clear()
        self._paused = False
        # cockpit text cache (for ReadText)
        self._cockpit_text_cache: Dict[str, str] = {}
        # group execution tracking for loop bodies
        self._group_active: Dict[int, int] = {}
        self._group_on_idle: Dict[int, list] = {}
        self._next_gid: int = 1

        self.on_state_changed.emit("stopped")
        self.on_active_tokens_changed.emit(0)
        self.on_reset_node_visuals.emit()
        QtCore.QTimer.singleShot(0, lambda: self.sigRunFinished.emit(dict(self.results)))

    
    def _notify_group_idle(self, gid: int) -> None:
        cbs = self._group_on_idle.get(gid, []) or []
        # Clear first to avoid re-entrancy double calls
        self._group_on_idle[gid] = []
        for cb in cbs:
            try:
                cb(gid)
            except Exception:
                pass
    # ---- group execution helpers (for loop bodies) --------------------
    def spawn_group(self, owner_node, out_port: str, *, on_idle=None) -> int:
        """Spawn a subgraph from ``owner_node``'s exec out_port into a new group.
        All tokens created from this out_port (and their descendants) will carry the group's gid.
        When the group's active token count drops to 0, ``on_idle`` is called (if provided).
        """
        gid = self._next_gid
        self._next_gid += 1
        self._group_active[gid] = 0
        if on_idle is not None:
            self._group_on_idle[gid] = [on_idle]
        else:
            self._group_on_idle[gid] = []

        nid = getattr(owner_node, "_nid", None)
        if not nid:
            return gid
        # Fire exec edges from (nid, out_port)
        created = 0
        for (dst_id, dst_port) in self.exec_outgoing.get((nid, out_port), []):
            child = self._new_token(dst_id, {}, gid=gid)
            self.post_ready(child)
            created += 1
        if created == 0:
            # No children → idle immediately
            QtCore.QTimer.singleShot(0, lambda gid=gid: self._notify_group_idle(gid))
        return gid

    # pause/resume ------------------------------------------------------
    def pause_all(self) -> None:
        self._paused = True
        for node in self.nodes.values():
            try:
                node.pause()
            except Exception:
                pass
        self._emit_state("paused")

    def resume_all(self) -> None:
        self._paused = False
        # cockpit text cache (for ReadText)
        self._cockpit_text_cache: Dict[str, str] = {}
        # group execution tracking for loop bodies
        self._group_active: Dict[int, int] = {}
        self._group_on_idle: Dict[int, list] = {}
        self._next_gid: int = 1

        for node in self.nodes.values():
            try:
                node.resume()
            except Exception:
                pass
        if self._ready:
            QtCore.QTimer.singleShot(0, self.drain)
        self._emit_state()

    # ---- helpers -------------------------------------------------------
    def _inc_active(self, delta: int = 1) -> None:
        self._active_tokens += delta
        self.on_active_tokens_changed.emit(self._active_tokens)
        if self._active_tokens > 0:
            self._emit_state("running")

    def _emit_state(self, forced: Optional[str] = None) -> None:
        if forced:
            self.on_state_changed.emit(forced)
            return
        if self._paused:
            self.on_state_changed.emit("paused")
        elif self._active_tokens > 0:
            self.on_state_changed.emit("running")
        elif self._continuous_run:
            self.on_state_changed.emit("idle")
        else:
            self.on_state_changed.emit("stopped")

    def _emit_run_finished(self) -> None:
        QtCore.QTimer.singleShot(0, lambda: self.sigRunFinished.emit(dict(self.results)))

    def _maybe_finish(self) -> None:
        if self._active_tokens == 0 and not self._ready:
            if not self._continuous_run:
                self._emit_run_finished()
                self._emit_state("stopped")
            else:
                self._emit_state("idle")

    # ---- cockpit helpers ----------------------------------------------
    def ui_cockpit_set_led(self, id: str, on: bool, color: str | None = None) -> None:
        try:
            self.on_cockpit_led_set.emit(str(id), bool(on), color)
        except Exception:
            pass

    def ui_cockpit_set_text(self, id: str, text: object, clear: bool=False, append: bool=False) -> None:
        try:
            self.on_cockpit_text_set.emit(str(id), text, bool(clear), bool(append))
        except Exception:
            pass

    def set_cockpit_text_cache(self, id: str, text: str) -> None:
        self._cockpit_text_cache[str(id)] = text

    def ui_cockpit_get_text(self, id: str) -> str | None:
        return self._cockpit_text_cache.get(str(id))
