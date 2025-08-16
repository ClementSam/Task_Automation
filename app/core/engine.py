from dataclasses import dataclass, field
from typing import Dict, List, Any, Tuple, DefaultDict, Optional
from collections import defaultdict
from .registry import registry
from typing import Optional

DEFAULT_PREFIX = "in_default:"

@dataclass
class NodeSpec:
    id: str
    type_name: str
    params: Dict[str, Any] = field(default_factory=dict)

@dataclass
class EdgeSpec:
    kind: str         # "data" ou "exec"
    src_id: str
    src_port: str
    dst_id: str
    dst_port: str

class ExecutionEngine:
    """
    Sépare data graph (DAG) et exec graph (événements).
    Hooks pour visualisation (on_node_start/finish, on_edge_fired).
    """
    def __init__(self, nodes: List[NodeSpec], edges: List[EdgeSpec], hooks: Optional[object] = None):
        self.nodes = {n.id: n for n in nodes}
        self.edges = edges
        self.instances = {}
        self.results: Dict[str, Dict[str, Any]] = {}
        self.hooks = hooks
        self._cancelled = False
        self.vars: Dict[str, Any] = {}

        self.data_incoming: Dict[Tuple[str, str], Tuple[str, str]] = {}
        self.exec_outgoing: DefaultDict[Tuple[str, str], List[Tuple[str, str]]] = defaultdict(list)
        self.pure_nodes: List[str] = []
        self.exec_nodes: List[str] = []

    def request_cancel(self):
        self._cancelled = True

    def _classify(self):
        for nid, spec in self.nodes.items():
            self.instances[nid] = registry.create(spec.type_name, **spec.params)
            try:
                setattr(self.instances[nid], '_engine', self)
            except Exception:
                pass

        for e in self.edges:
            if e.kind == "data":
                self.data_incoming[(e.dst_id, e.dst_port)] = (e.src_id, e.src_port)
            else:
                self.exec_outgoing[(e.src_id, e.src_port)].append((e.dst_id, e.dst_port))

        for nid, inst in self.instances.items():
            if inst.exec_inputs() or inst.exec_outputs():
                self.exec_nodes.append(nid)
            else:
                self.pure_nodes.append(nid)

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
        if len(order) != len(subset):
            raise RuntimeError("Cycle détecté dans le sous-graphe de données (noeuds purs).")
        return order

    def _gather_inputs(self, nid: str) -> Dict[str, Any]:
        node = self.instances[nid]
        params = node.params()
        kwargs = {}
        for in_name in node.inputs().keys():
            # câble ?
            if (nid, in_name) in self.data_incoming:
                src_id, src_port = self.data_incoming[(nid, in_name)]
                kwargs[in_name] = self.results.get(src_id, {}).get(src_port, None)
            else:
                # sinon valeur par défaut si présente
                key = DEFAULT_PREFIX + in_name
                kwargs[in_name] = params.get(key, None)
        return kwargs

    def run(self) -> Dict[str, Dict[str, Any]]:
        self._classify()

        if self.pure_nodes:
            order = self._topological_order_subset(self.pure_nodes)
            for nid in order:
                node = self.instances[nid]
                kwargs = self._gather_inputs(nid)
                out = node.process(**kwargs) or {}
                self.results[nid] = out

        entry_nodes = [nid for nid in self.exec_nodes if not self.instances[nid].exec_inputs()]
        queue: List[Tuple[str, Optional[str]]] = [(nid, None) for nid in entry_nodes]
        steps = 0; max_steps = 10000

        while queue:
            if getattr(self, '_cancelled', False):
                break
            steps += 1
            if steps > max_steps:
                raise RuntimeError("Trop d'étapes d'exécution (possible boucle).")

            nid, came_from = queue.pop(0)
            node = self.instances[nid]
            kwargs = self._gather_inputs(nid)

            if self.hooks and hasattr(self.hooks, "on_node_start"):
                try: self.hooks.on_node_start(nid)
                except Exception: pass

            next_ports, out = node.on_exec(**kwargs)

            # notify outputs to hooks if available
            if self.hooks and hasattr(self.hooks, "on_node_output"):
                try: self.hooks.on_node_output(nid, out or {})
                except Exception: pass

            if self.hooks and hasattr(self.hooks, "on_node_finish"):
                try: self.hooks.on_node_finish(nid)
                except Exception: pass



            prev = self.results.get(nid, {})
            prev.update(out or {})
            self.results[nid] = prev

            for exec_port in next_ports or []:
                for (dst_id, dst_port) in self.exec_outgoing.get((nid, exec_port), []):
                    if self.hooks and hasattr(self.hooks, "on_edge_fired"):
                        try: self.hooks.on_edge_fired(nid, exec_port, dst_id, dst_port)
                        except Exception: pass
                    queue.append((dst_id, dst_port))

        return self.results
