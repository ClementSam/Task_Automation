from PyQt5 import QtCore

from app.nodes.control import Branch, BeginPlay, ForLoop
from app.nodes.variables_runtime import SetVariable
from app.core.scheduler import Scheduler
from app.core.engine import NodeSpec, EdgeSpec


def test_branch_condition():
    node = Branch()
    assert node.on_exec(condition=None) == ([], {})
    assert node.on_exec(condition=True) == (["true"], {})


def _app():
    app = QtCore.QCoreApplication.instance()
    if app is None:
        app = QtCore.QCoreApplication([])
    return app


def _run_scheduler(sched: Scheduler):
    app = _app()
    for _ in range(1000):
        if sched._active_tokens == 0 and not sched._ready:
            break
        app.processEvents()


def test_forloop_basic():
    _app()
    sched = Scheduler()
    nodes = [
        NodeSpec(id="begin", type_name="BeginPlay", params={}),
        NodeSpec(id="loop", type_name="ForLoop", params={"in_default:first": 0, "in_default:last": 2}),
        NodeSpec(id="seti", type_name="SetVariable", params={"name": "last_index", "type": "Int"}),
        NodeSpec(id="setdone", type_name="SetVariable", params={"name": "done", "type": "Bool", "in_default:value": True}),
    ]
    edges = [
        EdgeSpec(kind="exec", src_id="begin", src_port="out", dst_id="loop", dst_port="in"),
        EdgeSpec(kind="exec", src_id="loop", src_port="loop_body", dst_id="seti", dst_port="in"),
        EdgeSpec(kind="data", src_id="loop", src_port="index", dst_id="seti", dst_port="value"),
        EdgeSpec(kind="exec", src_id="loop", src_port="completed", dst_id="setdone", dst_port="in"),
    ]
    sched.setup(nodes, edges, {})
    sched.start_run()
    _run_scheduler(sched)
    assert sched.vars["last_index"] == 2
    assert sched.vars["done"] is True
