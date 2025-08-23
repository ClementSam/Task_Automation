from PyQt5 import QtCore

from app.core.engine import NodeSpec, EdgeSpec
from app.core.scheduler import Scheduler


def _app():
    app = QtCore.QCoreApplication.instance()
    if app is None:
        app = QtCore.QCoreApplication([])
    return app


def test_custom_event_triggering():
    app = _app()
    nodes = [
        NodeSpec(id="n1", type_name="BeginPlay"),
        NodeSpec(id="n2", type_name="CallCustomEvent", params={"name": "Evt"}),
        NodeSpec(id="n3", type_name="CustomEvent", params={"name": "Evt"}),
        NodeSpec(id="n4", type_name="Print", params={"in_default:text": "hello"}),
    ]
    edges = [
        EdgeSpec(kind="exec", src_id="n1", src_port="out", dst_id="n2", dst_port="exec_in"),
        EdgeSpec(kind="exec", src_id="n3", src_port="exec_out", dst_id="n4", dst_port="in"),
    ]
    sched = Scheduler()
    sched.setup(nodes, edges, {})
    sched.start_run()
    for _ in range(100):
        if sched._active_tokens == 0 and not sched._ready:
            break
        app.processEvents()
    assert sched.results.get("n4", {}).get("printed") == "hello"
