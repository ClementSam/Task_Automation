from PyQt5 import QtWidgets, QtCore
import uuid
from ..core.cockpit_model import CockpitItemModel
from .cockpit_canvas import CockpitCanvas
from .cockpit_items.button import CockpitButtonItem

class _CockpitLinkingMixin:
    def build_name_index(self):
        """Return a *snapshot* mapping (name->id, id->name) of current cockpit items.

        Names are the user-facing titles at the time of the call. For buttons,
        we use the current event name (label) resolved by the item.
        """
        name_to_id = {}
        id_to_name = {}
        try:
            items = getattr(self, "_items_by_id", {})  # id -> item
        except Exception:
            items = {}
        for mid, item in items.items():
            # Determine snapshot name
            name = None
            # Prefer button event name if available
            if hasattr(item, "_event_name"):
                try:
                    name = item._event_name()
                except Exception:
                    name = None
            if not name:
                try:
                    name = (item.model.display_name or item.model.event_key or "").strip()
                except Exception:
                    name = ""
            if not name:
                continue
            norm = _normalize_cockpit_key(name)
            name_to_id[norm] = mid
            id_to_name[mid] = name
        return name_to_id, id_to_name

    def iter_items(self):
        try:
            return list(getattr(self, "_items_by_id", {}).items())
        except Exception:
            return []


class CockpitWidget(QtWidgets.QDockWidget, _CockpitLinkingMixin):
    buttonClicked = QtCore.pyqtSignal(str)       # event name
    textEdited = QtCore.pyqtSignal(str, str)     # id, text

    def __init__(self, scheduler, parent=None):
        super().__init__("Cockpit", parent)
        self._scheduler = scheduler
        self._items_by_id = {}

        # Canvas
        self._view = CockpitCanvas(scheduler, self)

        # Header toolbar
        header = QtWidgets.QWidget(self)
        hl = QtWidgets.QHBoxLayout(header)
        hl.setContentsMargins(6, 6, 6, 6)
        btn_add = QtWidgets.QPushButton("+ Button", header)
        btn_led = QtWidgets.QPushButton("+ LED", header)
        btn_txt = QtWidgets.QPushButton("+ Text", header)
        hl.addWidget(btn_add); hl.addWidget(btn_led); hl.addWidget(btn_txt); hl.addStretch(1)

        # Container
        container = QtWidgets.QWidget(self)
        vl = QtWidgets.QVBoxLayout(container)
        vl.setContentsMargins(0, 0, 0, 0)
        vl.addWidget(header)
        vl.addWidget(self._view)
        self.setWidget(container)

        # Wiring
        btn_add.clicked.connect(lambda: self._add_item_center("UIButton"))
        btn_led.clicked.connect(lambda: self._add_item_center("UILed"))
        btn_txt.clicked.connect(lambda: self._add_item_center("UIText"))
        self._view.itemCreated.connect(self._on_item_created)

    # ---- public API (compat) ----------------------------------------
    def set_led(self, id: str, on: bool, color):
        it = self._items_by_id.get(id)
        if it and hasattr(it, "set_led"):
            it.set_led(on, color)

    def apply_text_action(self, id: str, text, clear: bool, append: bool):
        it = self._items_by_id.get(id)
        if it and hasattr(it, "apply_text_action"):
            it.apply_text_action(text, clear, append)

    def serialize(self) -> dict:
        return self._view.serialize()

    def deserialize(self, data: dict):
        # Backward-compat: old format {"elements":[{type:'btn'|'text'|'led'|'label', id, pos:[x,y], props:{...}}]}
        def _from_old(d):
            items = []
            for el in (d or {}).get("elements", []):
                t = el.get("type")
                type_name = {"btn": "UIButton", "led": "UILed", "text": "UIText", "label": "UIText"}.get(t, "UIButton")
                props = el.get("props", {}) or {}
                x, y = (float(el.get("pos", [0, 0])[0]), float(el.get("pos", [0, 0])[1]))
                disp = props.get("text") or type_name
                items.append({
                    "id": el.get("id", ""),
                    "type": type_name,
                    "display_name": disp,
                    "event_key": "",
                    "props": props,
                    "x": x, "y": y
                })
            return {"items": items}

        if data and "elements" in data and "items" not in data:
            data = _from_old(data)

        self._view.deserialize(data)
        # rebuild id index and wire signals
        self._items_by_id.clear()
        for it in self._view.scene().items():
            if hasattr(it, "model"):
                mid = it.model.id or str(uuid.uuid4())
                it.model.id = mid
                self._items_by_id[mid] = it
                if hasattr(it, "renamed"):
                    it.renamed.connect(lambda txt, iid=mid: self.textEdited.emit(iid, txt))
                if isinstance(it, CockpitButtonItem):
                    it.clicked.connect(self.buttonClicked.emit)

    # ---- helpers -----------------------------------------------------
    def _on_item_created(self, model, item):
        self._items_by_id[model.id] = item
        if hasattr(item, "renamed"):
            item.renamed.connect(lambda txt, iid=model.id: self.textEdited.emit(iid, txt))
        if isinstance(item, CockpitButtonItem):
            item.clicked.connect(self.buttonClicked.emit)

    def _add_item_center(self, type_name: str):
        rect = self._view.viewport().rect()
        center = rect.center()
        scene_pos = self._view.mapToScene(center)
        self._view.add_item_at(type_name, scene_pos.x(), scene_pos.y())

    # Context menu on dock area -> forward to canvas
    def contextMenuEvent(self, ev):
        m = QtWidgets.QMenu(self)
        act_btn = m.addAction("Add Button")
        act_led = m.addAction("Add LED")
        act_txt = m.addAction("Add Text")
        chosen = m.exec_(ev.globalPos())
        if chosen:
            sp = self._view.mapToScene(self._view.mapFromGlobal(ev.globalPos()))
            if chosen == act_btn:
                self._view.add_item_at("UIButton", sp.x(), sp.y())
            elif chosen == act_led:
                self._view.add_item_at("UILed", sp.x(), sp.y())
            elif chosen == act_txt:
                self._view.add_item_at("UIText", sp.x(), sp.y())


# --- Linking helpers (name<->id snapshot) ---------------------------------
def _normalize_cockpit_key(key: str) -> str:
    try:
        return (str(key) or "").strip().lower()
    except Exception:
        return ""

