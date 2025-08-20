import json
from dataclasses import asdict
from pathlib import Path
from typing import Dict, List, Tuple

from .engine import EdgeSpec, NodeSpec


def save_graph(
    nodes: List[NodeSpec],
    edges: List[EdgeSpec],
    path: str | Path,
    *,
    variables: List[Dict[str, object]] | None = None,
    ui: Dict[str, object] | None = None,
) -> None:
    """Save a graph to JSON file.

    Besides the basic node/edge information, optional ``variables`` and
    ``ui`` dictionaries can be provided in order to persist editor state
    such as node positions, edge control points or comments.
    """
    data: Dict[str, object] = {
        "nodes": [],
        "edges": [],
    }
    ui = ui or {}
    node_ui: Dict[str, Dict[str, object]] = ui.get("nodes", {})  # type: ignore[assignment]
    edge_ui: List[Dict[str, object]] = ui.get("edges", [])  # type: ignore[assignment]

    for n in nodes:
        nd = asdict(n)
        if n.id in node_ui:
            nd.update(node_ui[n.id])
        data["nodes"].append(nd)

    for i, e in enumerate(edges):
        ed = asdict(e)
        if i < len(edge_ui):
            ed.update(edge_ui[i])
        data["edges"].append(ed)

    if variables:
        data["variables"] = variables
    if ui.get("comments"):
        data["comments"] = ui["comments"]

    p = Path(path)
    with p.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def load_graph(
    path: str | Path,
) -> Tuple[List[NodeSpec], List[EdgeSpec], List[Dict[str, object]], Dict[str, object]]:
    """Load a graph from a JSON file.

    Returns the list of nodes, edges, variables and UI information found in
    the file. Unknown keys are ignored. Missing sections default to empty
    structures.
    """
    p = Path(path)
    with p.open("r", encoding="utf-8") as f:
        data = json.load(f)

    nodes: List[NodeSpec] = []
    node_ui: Dict[str, Dict[str, object]] = {}
    for nd in data.get("nodes", []):
        pos = {k: nd.pop(k) for k in list(nd.keys()) if k not in {"id", "type_name", "params"}}
        node = NodeSpec(id=nd.get("id"), type_name=nd.get("type_name"), params=nd.get("params", {}))
        nodes.append(node)
        if pos:
            node_ui[node.id] = pos

    edges: List[EdgeSpec] = []
    edge_ui: List[Dict[str, object]] = []
    for ed in data.get("edges", []):
        extra = {k: ed.pop(k) for k in list(ed.keys()) if k not in {"kind", "src_id", "src_port", "dst_id", "dst_port"}}
        edge = EdgeSpec(
            kind=ed.get("kind"),
            src_id=ed.get("src_id"),
            src_port=ed.get("src_port"),
            dst_id=ed.get("dst_id"),
            dst_port=ed.get("dst_port"),
        )
        edges.append(edge)
        edge_ui.append(extra)

    variables = data.get("variables", [])
    ui: Dict[str, object] = {
        "nodes": node_ui,
        "edges": edge_ui,
        "comments": data.get("comments", []),
    }
    return nodes, edges, variables, ui
