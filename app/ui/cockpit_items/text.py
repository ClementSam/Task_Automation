
from PyQt5 import QtWidgets
from ...core.cockpit_registry import cockpit_registry
from .base import CockpitGraphicsItem

@cockpit_registry.register("UIText")
class CockpitTextItem(CockpitGraphicsItem):
    def __init__(self, scheduler, model):
        super().__init__(scheduler, model)
        # Bigger card for text
        self.set_size(360, 220)
        editor = QtWidgets.QPlainTextEdit()
        # Keep scheduler cache in sync with manual edits
        def _push_cache():
            try:
                self.scheduler.set_cockpit_text_cache(self.model.id, editor.toPlainText())
            except Exception:
                pass
        editor.textChanged.connect(_push_cache)
        editor.setReadOnly(False)
        self.set_body_widget(editor)
        self._text = editor

    def apply_text_action(self, text, clear: bool, append: bool):
        if clear:
            self._text.setPlainText("")
        if append:
            self._text.appendPlainText(str(text))
        else:
            self._text.setPlainText(str(text))
