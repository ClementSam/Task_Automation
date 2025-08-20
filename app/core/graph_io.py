import json
from dataclasses import asdict
from pathlib import Path
from typing import List, Tuple

from .engine import NodeSpec, EdgeSpec


def save_graph(nodes: List[NodeSpec], edges: List[EdgeSpec], path: str | Path) -> None:
    """Save a graph to JSON file.

    Only node identifiers, their type, parameters and edge endpoints are
    stored. It is up to the application to recreate a visual layout from
    this information when loading.
    """
    data = {
        "nodes": [asdict(n) for n in nodes],
        "edges": [asdict(e) for e in edges],
    }
    p = Path(path)
    with p.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def load_graph(path: str | Path) -> Tuple[List[NodeSpec], List[EdgeSpec]]:
    """Load a graph from a JSON file.

    Returns the list of nodes and edges found in the file. Unknown keys are
    ignored. Missing sections default to empty lists.
    """
    p = Path(path)
    with p.open("r", encoding="utf-8") as f:
        data = json.load(f)
    nodes = [NodeSpec(**n) for n in data.get("nodes", [])]
    edges = [EdgeSpec(**e) for e in data.get("edges", [])]
    return nodes, edges
