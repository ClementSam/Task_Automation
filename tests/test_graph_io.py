from pathlib import Path

from app.core.engine import NodeSpec, EdgeSpec, ExecutionEngine, DEFAULT_PREFIX
from app.core.graph_io import save_graph, load_graph

# Ensure node classes are registered
from app.nodes import control as _control_nodes  # noqa: F401
from app.nodes import math as _math_nodes  # noqa: F401


def test_save_and_load_graph(tmp_path: Path):
    nodes = [
        NodeSpec(id="n1", type_name="BeginPlay"),
        NodeSpec(id="n2", type_name="Add", params={
            DEFAULT_PREFIX + "a": 1,
            DEFAULT_PREFIX + "b": 2,
        }),
        NodeSpec(id="n3", type_name="Print"),
    ]
    edges = [
        EdgeSpec(kind="exec", src_id="n1", src_port="out", dst_id="n3", dst_port="in"),
        EdgeSpec(kind="data", src_id="n2", src_port="sum", dst_id="n3", dst_port="text"),
    ]

    path = tmp_path / "graph.json"
    save_graph(nodes, edges, path)
    loaded_nodes, loaded_edges = load_graph(path)

    assert loaded_nodes == nodes
    assert loaded_edges == edges

    engine = ExecutionEngine(loaded_nodes, loaded_edges, vars_init={})
    results = engine.run()
    assert results["n3"]["printed"] == 3.0
