from PyQt5 import QtCore

from .scheduler import Scheduler
from .logctl import enabled, thread_label



class _HooksBridge:
    """Forward scheduler callbacks to EngineRunner signals."""

    def __init__(self, runner):
        self._runner = runner

    def _node_label(self, nid: str) -> str:
        try:
            sched = getattr(self._runner, "_scheduler", None)
            node = getattr(sched, "nodes", {}).get(nid) if sched else None
            if node is None:
                return f"n{nid}"
            # Prefer type_name, then title, then class name
            lab = None
            if hasattr(node.__class__, "type_name") and callable(node.__class__.type_name):
                try:
                    lab = node.__class__.type_name()
                except Exception:
                    lab = None
            if not lab and hasattr(node.__class__, "title") and callable(node.__class__.title):
                try:
                    lab = node.__class__.title()
                except Exception:
                    lab = None
            if not lab:
                lab = node.__class__.__name__
            return str(lab).strip()
        except Exception:
            return f"n{nid}"

    def on_node_start(self, nid: str):
        # Execution trace
        if enabled('trace'):
            lab = self._node_label(nid)
            print(f"[{lab}] {nid} -> exec on {thread_label()}")
        # Special-case Delay enters wait
        if enabled('wait'):
            lab = self._node_label(nid)
            if lab.lower().replace(' ', '') == 'delay':
                print(f"[Delay] {nid} -> Wait mode")

    def on_node_output(self, nid: str, out: dict):
        # User Print node: show message
        try:
            if enabled('print'):
                lab = self._node_label(nid)
                if lab.lower().replace(' ', '') == 'print':
                    msg = out.get('printed', out.get('text', ''))
                    print(f"[Print] {nid} -> {msg}")
        except Exception:
            pass
        self._runner.sigNodeOutput.emit(nid, out)

    def on_node_finish(self, nid: str):
        # Wakeup for Delay
        if enabled('wait'):
            lab = self._node_label(nid)
            if lab.lower().replace(' ', '') == 'delay':
                print(f"[Delay] {nid} -> Wakeup mode")

    def on_edge_fired(self, src_id: str, src_port: str, dst_id: str, dst_port: str):
        self._runner.sigEdgeFired.emit(src_id, src_port, dst_id, dst_port)

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
    # Cockpit forwards (Scheduler -> UI)
    sigCockpitLedSet = QtCore.pyqtSignal(str, bool, object)
    sigCockpitTextSet = QtCore.pyqtSignal(str, object, bool, bool)
    sigError = QtCore.pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._scheduler: Scheduler | None = None
        self._continuous_desired = False

    def setContinuousRun(self, enabled: bool):
        """Remember and apply the desired continuous mode.

        Can be called before or during execution. If the scheduler is
        already running the mode is applied immediately; otherwise it is
        stored and applied when :meth:`start` is invoked.
        """
        self._continuous_desired = bool(enabled)
        if self._scheduler:
            self._scheduler.set_continuous_run(self._continuous_desired)

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
            self._scheduler.on_node_listening_changed.connect(lambda nid, on, hooks=hooks: print(f"[{hooks._node_label(nid)}] {nid} -> {'Wait mode' if on else 'Wakeup mode'}"))
            # Debug wait/wakeup logs for listening nodes
            if enabled('wait'):
                self._scheduler.on_node_listening_changed.connect(lambda nid, on, hooks=hooks: print(f"[{hooks._node_label(nid)}] {nid} -> {'Wait mode' if on else 'Wakeup mode'}"))
            # cockpit
            self._scheduler.on_cockpit_led_set.connect(self.sigCockpitLedSet)
            self._scheduler.on_cockpit_text_set.connect(self.sigCockpitTextSet)
            # apply user choice before the run starts
            self._scheduler.set_continuous_run(self._continuous_desired)
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


    def cockpitButtonClicked(self, id: str):
        if self._scheduler:
            try:
                self._scheduler.on_cockpit_button_clicked.emit(str(id))
            except Exception:
                pass

    def setCockpitTextCache(self, id: str, text: str):
        if self._scheduler:
            try:
                self._scheduler.set_cockpit_text_cache(str(id), str(text))
            except Exception:
                pass

    def on_node_finish(self, nid: str):
        # Wakeup for Delay
        if enabled('wait'):
            lab = self._node_label(nid)
            if lab.lower().replace(' ', '') == 'delay':
                print(f"[Delay] {nid} -> Wakeup mode")
        # nothing else here; EngineRunner also forwards finished via signals

    def on_node_listening_changed(self, nid: str, on: bool):
        # Nodes that wait for signals (CustomEvent, OnCockpitButton, Serial events)
        if enabled('wait'):
            lab = self._node_label(nid)
            print(f"[{lab}] {nid} -> {'Wait mode' if on else 'Wakeup mode'}")
