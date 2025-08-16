from PyQt5 import QtCore

from .scheduler import Scheduler


class _HooksBridge:
    """Forward scheduler callbacks to EngineRunner signals."""

    def __init__(self, runner):
        self._runner = runner

    def on_node_start(self, nid: str):
        self._runner.sigNodeStarted.emit(nid)

    def on_node_finish(self, nid: str):
        self._runner.sigNodeFinished.emit(nid)

    def on_edge_fired(self, src_id: str, src_port: str, dst_id: str, dst_port: str):
        self._runner.sigEdgeFired.emit(src_id, src_port, dst_id, dst_port)

    def on_node_output(self, nid: str, out: dict):
        self._runner.sigNodeOutput.emit(nid, out)


class EngineRunner(QtCore.QObject):
    """Asynchronous engine powered by :class:`Scheduler` in the main thread."""

    sigRunStarted = QtCore.pyqtSignal()
    sigRunFinished = QtCore.pyqtSignal(dict)
    sigNodeStarted = QtCore.pyqtSignal(str)
    sigNodeFinished = QtCore.pyqtSignal(str)
    sigEdgeFired = QtCore.pyqtSignal(str, str, str, str)
    sigNodeOutput = QtCore.pyqtSignal(str, dict)
    sigError = QtCore.pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._scheduler: Scheduler | None = None

    def start(self, nodes, edges, vars_init=None):
        try:
            self.sigRunStarted.emit()
            hooks = _HooksBridge(self)
            self._scheduler = Scheduler(hooks=hooks)
            self._scheduler.sigRunFinished.connect(self.sigRunFinished)
            self._scheduler.setup(nodes, edges, vars_init or {})
            QtCore.QTimer.singleShot(0, self._scheduler.start_run)
        except Exception as e:  # pragma: no cover - forward error
            self.sigError.emit(str(e))

    def stop(self):
        if self._scheduler:
            self._scheduler.cancel_all()

    def deleteLater(self):  # pragma: no cover - Qt cleanup
        self._scheduler = None
        super().deleteLater()

