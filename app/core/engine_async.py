from PyQt5 import QtCore

from .scheduler import Scheduler


class _HooksBridge:
    """Forward scheduler callbacks to EngineRunner signals."""

    def __init__(self, runner):
        self._runner = runner

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
    sigStateChanged = QtCore.pyqtSignal(str)
    sigActiveTokens = QtCore.pyqtSignal(int)
    sigResetNodeVisuals = QtCore.pyqtSignal()
    sigNodeListening = QtCore.pyqtSignal(str, bool)
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
            self._scheduler.on_token_started.connect(lambda nid, tid: self.sigNodeStarted.emit(nid))
            self._scheduler.on_token_finished.connect(lambda nid, tid: self.sigNodeFinished.emit(nid))
            self._scheduler.on_state_changed.connect(self.sigStateChanged)
            self._scheduler.on_active_tokens_changed.connect(self.sigActiveTokens)
            self._scheduler.on_reset_node_visuals.connect(self.sigResetNodeVisuals)
            self._scheduler.on_node_listening_changed.connect(self.sigNodeListening)
            self._scheduler.setup(nodes, edges, vars_init or {})
            QtCore.QTimer.singleShot(0, self._scheduler.start_run)
        except Exception as e:  # pragma: no cover - forward error
            self.sigError.emit(str(e))

    def stop(self):
        if self._scheduler:
            self._scheduler.cancel_all()

    def pause(self):
        if self._scheduler:
            self._scheduler.pause_all()

    def resume(self):
        if self._scheduler:
            self._scheduler.resume_all()

    def deleteLater(self):  # pragma: no cover - Qt cleanup
        self._scheduler = None
        super().deleteLater()

