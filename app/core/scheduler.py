from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Any, Optional, Tuple
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


class Scheduler(QtCore.QObject):
    """Single-threaded scheduler driving node execution."""

    sigRunFinished = QtCore.pyqtSignal(dict)

    def __init__(self, parent=None, hooks: Optional[object] = None):
        super().__init__(parent)
        self.hooks = hooks
        self.ready: deque[int] = deque()
        self.nodes: Dict[str, Any] = {}
        self.tokens: Dict[int, Token] = {}
        self.results: Dict[str, Dict[str, Any]] = {}
        self.vars: Dict[str, Any] = {}
        self.data_incoming: Dict[Tuple[str, str], Tuple[str, str]] = {}
        self.exec_outgoing: Dict[Tuple[str, str], List[Tuple[str, str]]] = defaultdict(list)
        self._next_token = 1
        self._draining = False
        self._active = 0
        self._pure_nodes: List[str] = []
        self._exec_nodes: List[str] = []
        self._paused = False

    # ---- graph setup --------------------------------------------------
    def setup(self, nodes: List[NodeSpec], edges: List[EdgeSpec], vars_init: Dict[str, Any]):
        self.ready.clear()
        self.tokens.clear()
        self.results.clear()
        self.vars = dict(vars_init or {})
        self.data_incoming.clear()
        self.exec_outgoing.clear()
        self.nodes.clear()
        self._pure_nodes.clear()
        self._exec_nodes.clear()
        self._next_token = 1
        self._active = 0
        self._paused = False

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

    # ---- token helpers -------------------------------------------------
    def _new_token(self, nid: str, data: Optional[Dict[str, Any]] = None) -> int:
        tid = self._next_token
        self._next_token += 1
        self.tokens[tid] = Token(tid, nid, data or {})
        self._active += 1
        return tid

    def post_ready(self, tid: int) -> None:
        self.ready.append(tid)
        if not self._paused:
            QtCore.QTimer.singleShot(0, self.drain)

    # ---- running -------------------------------------------------------
    def start_run(self):
        # evaluate pure nodes synchronously
        if self._pure_nodes:
            order = self._topological_order_subset(self._pure_nodes)
            for nid in order:
                node = self.nodes[nid]
                out = node.process(**self._gather_inputs(nid)) or {}
                self.results[nid] = out
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
            while self.ready:
                tid = self.ready.popleft()
                tok = self.tokens.get(tid)
                if not tok or tok.cancelled:
                    continue
                nid = tok.target
                node = self.nodes[nid]
                if node.busy:
                    node.enqueue_local(tid)
                    continue
                node.busy = True
                if self.hooks and hasattr(self.hooks, "on_node_start"):
                    try:
                        self.hooks.on_node_start(nid)
                    except Exception:
                        pass
                kwargs = self._gather_inputs(nid)
                node.start(tid, **kwargs)
        finally:
            self._draining = False

    # called by nodes when finished
    def on_node_finished(self, nid: str, tid: int, next_ports: Optional[List[str]], out: Optional[Dict[str, Any]]):
        node = self.nodes[nid]
        node.busy = False
        self.tokens.pop(tid, None)
        self._active -= 1
        prev = self.results.get(nid, {})
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
        # start next token from local queue if any
        nxt = node.dequeue_local()
        if nxt is not None:
            node.busy = True
            if self.hooks and hasattr(self.hooks, "on_node_start"):
                try:
                    self.hooks.on_node_start(nid)
                except Exception:
                    pass
            kwargs = self._gather_inputs(nid)
            node.start(nxt, **kwargs)
        # propagate exec edges
        for port in next_ports or []:
            for (dst_id, dst_port) in self.exec_outgoing.get((nid, port), []):
                if self.hooks and hasattr(self.hooks, "on_edge_fired"):
                    try:
                        self.hooks.on_edge_fired(nid, port, dst_id, dst_port)
                    except Exception:
                        pass
                child = self._new_token(dst_id, {})
                self.post_ready(child)
        # run finished?
        if self._active == 0 and not self.ready:
            QtCore.QTimer.singleShot(0, lambda: self.sigRunFinished.emit(dict(self.results)))

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
        self.ready.clear()
        self._active = 0
        self._paused = False
        QtCore.QTimer.singleShot(0, lambda: self.sigRunFinished.emit(dict(self.results)))

    # pause/resume ------------------------------------------------------
    def pause_all(self) -> None:
        self._paused = True
        for node in self.nodes.values():
            try:
                node.pause()
            except Exception:
                pass

    def resume_all(self) -> None:
        self._paused = False
        for node in self.nodes.values():
            try:
                node.resume()
            except Exception:
                pass
        if self.ready:
            QtCore.QTimer.singleShot(0, self.drain)
