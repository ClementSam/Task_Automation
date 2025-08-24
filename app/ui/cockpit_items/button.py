from PyQt5 import QtWidgets, QtCore
from ...core.cockpit_registry import cockpit_registry
from .base import CockpitGraphicsItem

@cockpit_registry.register("UIButton")
class CockpitButtonItem(CockpitGraphicsItem):
    clicked = QtCore.pyqtSignal(str)  # event name

    def __init__(self, scheduler, model):
        super().__init__(scheduler, model)
        btn = QtWidgets.QPushButton(model.props.get("text") or "BTN")
        btn.setMinimumWidth(64)
        btn.clicked.connect(self._on_click)
        self.set_header_widget(btn)

    def _event_name(self) -> str:
        # Prefer current edited label text
        try:
            txt = (self.title.toPlainText() or "").strip()
        except Exception:
            txt = ""
        if txt:
            return txt
        return (self.model.event_key or self.model.display_name or "").strip()

    def _on_click(self):
        name = self._event_name()
        if name:
            self.clicked.emit(name)
