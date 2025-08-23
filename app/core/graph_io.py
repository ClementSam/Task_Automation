from __future__ import annotations

import json
import os
import tempfile
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple

from .engine import EdgeSpec, NodeSpec

Json = Dict[str, Any]

def _coerce_json(obj: Any) -> Any:
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, (list, tuple, set)):
        return [_coerce_json(x) for x in obj]
    if isinstance(obj, dict):
        return {str(k): _coerce_json(v) for k, v in obj.items() if not str(k).startswith("_")}
    if is_dataclass(obj):
        return {k: _coerce_json(v) for k, v in asdict(obj).items()}
    if isinstance(obj, Path):
        return str(obj)
    mod = type(obj).__module__
    if mod.startswith("PyQt5") or mod.startswith("PySide"):
        return None
    try:
        json.dumps(obj)
        return obj
    except Exception:
        return str(obj)

def _sanitize_params(params: Dict[str, Any] | None) -> Dict[str, Any]:
    params = params or {}
    return {k: _coerce_json(v) for k, v in params.items() if not str(k).startswith("_")}

def _node_to_dict(n: NodeSpec) -> Dict[str, Any]:
    return {
        "id": getattr(n, "id"),
        "type_name": getattr(n, "type_name"),
        "params": _sanitize_params(getattr(n, "params", {})),
    }

def _edge_to_dict(e: EdgeSpec) -> Dict[str, Any]:
    return {
        "kind": getattr(e, "kind", "data"),
        "src_id": getattr(e, "src_id"),
        "src_port": getattr(e, "src_port"),
        "dst_id": getattr(e, "dst_id"),
        "dst_port": getattr(e, "dst_port"),
    }

def save_graph(
    nodes: List[NodeSpec],
    edges: List[EdgeSpec],
    path: str | Path,
    *,
    variables: List[Dict[str, object]] | None = None,
    ui: Dict[str, object] | None = None,
) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    payload: Dict[str, Any] = {
        "nodes": [_node_to_dict(n) for n in nodes],
        "edges": [_edge_to_dict(e) for e in edges],
    }
    if variables is not None:
        payload["variables"] = [_coerce_json(v) for v in variables]
    if ui is not None:
        payload["ui"] = _coerce_json(ui)

    tmp = tempfile.NamedTemporaryFile("w", delete=False, dir=str(path.parent), encoding="utf-8")
    try:
        json.dump(payload, tmp, ensure_ascii=False, indent=2)
        tmp.flush()
        os.fsync(tmp.fileno())
        tmp.close()
        os.replace(tmp.name, path)
    finally:
        try:
            os.remove(tmp.name)
        except OSError:
            pass

def load_graph(path: str | Path) -> Tuple[List[NodeSpec], List[EdgeSpec], List[Dict[str, object]], Dict[str, object]]:
    path = Path(path)
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    nodes: List[NodeSpec] = []
    node_ui: Dict[str, Dict[str, Any]] = {}
    for nd in data.get("nodes", []):
        nid = str(nd.get("id"))
        tname = str(nd.get("type_name"))
        params = nd.get("params") or {}
        if not isinstance(params, dict):
            params = {}
        params = _sanitize_params(params)
        nodes.append(NodeSpec(id=nid, type_name=tname, params=params))
        pos = nd.get("pos") or nd.get("position")
        if isinstance(pos, (list, tuple)) and len(pos) >= 2:
            try:
                node_ui[nid] = {"pos": [float(pos[0]), float(pos[1])]}
            except Exception:
                pass

    edges: List[EdgeSpec] = []
    edge_ui: List[Dict[str, Any]] = []
    for ed in data.get("edges", []):
        kind = ed.get("kind", "data")
        src_id = ed.get("src_id")
        src_port = ed.get("src_port")
        dst_id = ed.get("dst_id")
        dst_port = ed.get("dst_port")
        if None in (src_id, src_port, dst_id, dst_port):
            continue
        edges.append(EdgeSpec(kind=kind, src_id=src_id, src_port=src_port, dst_id=dst_id, dst_port=dst_port))
        extra = {k: v for k, v in ed.items() if k not in {"kind", "src_id", "src_port", "dst_id", "dst_port"}}
        edge_ui.append(_coerce_json(extra) if extra else {})

    variables = data.get("variables") or data.get("vars") or []

    ui_block = data.get("ui")
    if isinstance(ui_block, dict):
        ui: Dict[str, Any] = {k: _coerce_json(v) for k, v in ui_block.items()}
        ui["nodes"] = ui.get("nodes") or node_ui
        ui["edges"] = ui.get("edges") or edge_ui
        ui["comments"] = ui.get("comments") or []
    else:
        ui = {
            "nodes": node_ui,
            "edges": edge_ui,
            "comments": data.get("comments", []),
        }

    return nodes, edges, variables, ui
