
from PyQt5 import QtCore
from .engine import ExecutionEngine

class _HooksBridge:
    def __init__(self, emitter): self._emitter = emitter
    def on_node_start(self, nid: str): self._emitter.sigNodeStarted.emit(nid)
    def on_node_finish(self, nid: str): self._emitter.sigNodeFinished.emit(nid)
    def on_edge_fired(self, src_id: str, src_port: str, dst_id: str, dst_port: str):
        self._emitter.sigEdgeFired.emit(src_id, src_port, dst_id, dst_port)
    def on_node_output(self, nid: str, out: dict): self._emitter.sigNodeOutput.emit(nid, out)

class EngineWorker(QtCore.QObject):
    sigRunStarted = QtCore.pyqtSignal()
    sigRunFinished = QtCore.pyqtSignal(dict)
    sigNodeStarted = QtCore.pyqtSignal(str)
    sigNodeFinished = QtCore.pyqtSignal(str)
    sigEdgeFired = QtCore.pyqtSignal(str, str, str, str)
    sigNodeOutput = QtCore.pyqtSignal(str, dict)
    sigError = QtCore.pyqtSignal(str)

    @QtCore.pyqtSlot(list, list)
    def start_run(self, nodes, edges):
        try:
            self.sigRunStarted.emit()
            hooks = _HooksBridge(self)
            self._engine = ExecutionEngine(nodes, edges, hooks=hooks)
            results = self._engine.run()
            self.sigRunFinished.emit(results)
            self._engine = None
        except Exception as e:
            self.sigError.emit(str(e))

    def cancel(self):
        try:
            if hasattr(self, "_engine") and self._engine and hasattr(self._engine, "request_cancel"):
                self._engine.request_cancel()
        except Exception:
            pass

class EngineRunner(QtCore.QObject):
    sigRunStarted = QtCore.pyqtSignal()
    sigRunFinished = QtCore.pyqtSignal(dict)
    sigNodeStarted = QtCore.pyqtSignal(str)
    sigNodeFinished = QtCore.pyqtSignal(str)
    sigEdgeFired = QtCore.pyqtSignal(str, str, str, str)
    sigNodeOutput = QtCore.pyqtSignal(str, dict)
    sigError = QtCore.pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._thread = QtCore.QThread(self)
        self._worker = EngineWorker()
        self._worker.moveToThread(self._thread)
        # bubble up
        self._worker.sigRunStarted.connect(self.sigRunStarted)
        self._worker.sigRunFinished.connect(self.sigRunFinished)
        self._worker.sigNodeStarted.connect(self.sigNodeStarted)
        self._worker.sigNodeFinished.connect(self.sigNodeFinished)
        self._worker.sigEdgeFired.connect(self.sigEdgeFired)
        self._worker.sigNodeOutput.connect(self.sigNodeOutput)
        self._worker.sigError.connect(self.sigError)
        self._thread.start()

    def start(self, nodes, edges):
        QtCore.QMetaObject.invokeMethod(self._worker, "start_run", QtCore.Qt.QueuedConnection,
                                        QtCore.Q_ARG(list, nodes), QtCore.Q_ARG(list, edges))

    def stop(self):
        self._worker.cancel()

    def deleteLater(self):
        try:
            self._thread.quit(); self._thread.wait(5000)
        except Exception:
            pass
        super().deleteLater()
