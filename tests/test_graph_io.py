from pathlib import Path

from app.core.engine import NodeSpec, EdgeSpec, ExecutionEngine, DEFAULT_PREFIX
from app.core.graph_io import save_graph, load_graph

# Ensure node classes are registered
from app.nodes import control as _control_nodes  # noqa: F401
from app.nodes import math as _math_nodes  # noqa: F401


def test_save_and_load_graph(tmp_path: Path):
    nodes = [
        NodeSpec(id="n1", type_name="BeginPlay"),
        NodeSpec(id="n2", type_name="Add_Float", params={
            DEFAULT_PREFIX + "a": 1,
            DEFAULT_PREFIX + "b": 2,
        }),
        NodeSpec(id="n3", type_name="Print"),
    ]
    edges = [
        EdgeSpec(kind="exec", src_id="n1", src_port="out", dst_id="n3", dst_port="in"),
        EdgeSpec(kind="data", src_id="n2", src_port="sum", dst_id="n3", dst_port="text"),
    ]

    variables = [{"name": "foo", "type": "Int", "init": 0}]
    ui = {
        "nodes": {
            "n1": {"pos": [10, 20]},
            "n2": {"pos": [30, 40]},
            "n3": {"pos": [50, 60]},
        },
        "edges": [{"points": []}, {"points": [[1.0, 2.0]]}],
        "comments": [
            {"rect": [0, 0, 100, 50], "color": "#FFFFFF", "text": "note"}
        ],
        "cockpit": {
            "elements": [
                {"type": "label", "id": "lbl:1", "pos": [0, 0], "props": {"text": "hello"}}
            ]
        },
    }

    path = tmp_path / "graph.json"
    save_graph(nodes, edges, path, variables=variables, ui=ui)
    loaded_nodes, loaded_edges, loaded_vars, loaded_ui = load_graph(path)

    assert loaded_nodes == nodes
    assert loaded_edges == edges
    assert loaded_vars == variables
    assert loaded_ui == ui

    engine = ExecutionEngine(loaded_nodes, loaded_edges, vars_init={})
    results = engine.run()
    assert results["n3"]["printed"] == 3.0
