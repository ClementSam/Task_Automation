from PyQt5 import QtWidgets, QtCore
from ..core.cockpit_model import CockpitItemModel
from .cockpit_items.factory import create_cockpit_item
import uuid

class CockpitCanvas(QtWidgets.QGraphicsView):
    itemCreated = QtCore.pyqtSignal(object, object)  # model, graphics item

    def __init__(self, scheduler, parent=None):
        super().__init__(parent)
        self.scheduler = scheduler
        self.setScene(QtWidgets.QGraphicsScene(self))
        self.setDragMode(QtWidgets.QGraphicsView.RubberBandDrag)
        self.setContextMenuPolicy(QtCore.Qt.DefaultContextMenu)

    def clear(self):
        self.scene().clear()

    def add_item(self, model: CockpitItemModel):
        item = create_cockpit_item(self.scheduler, model)
        self.scene().addItem(item)
        item.setPos(model.x, model.y)
        return item

    def add_item_at(self, type_name: str, x: float, y: float):
        friendly = {'UIButton':'Button','UILed':'Led','UIText':'Text'}
        model = CockpitItemModel(id=str(uuid.uuid4()), type_name=type_name, display_name=friendly.get(type_name, type_name), x=x, y=y)
        item = create_cockpit_item(self.scheduler, model)
        self.scene().addItem(item)
        item.setPos(x, y)
        self.itemCreated.emit(model, item)
        return item

    def serialize(self):
        items = []
        for it in self.scene().items():
            if hasattr(it, "model"):
                m = it.model
                p = it.pos()
                m.x, m.y = float(p.x()), float(p.y())
                items.append(m.to_dict())
        return {"items": items}

    def deserialize(self, data: dict):
        self.clear()
        for d in (data or {}).get("items", []):
            try:
                model = CockpitItemModel.from_dict(d)
                self.add_item(model)
            except Exception:
                pass

    def contextMenuEvent(self, ev):
        m = QtWidgets.QMenu(self)
        act_btn = m.addAction("Add Button")
        act_led = m.addAction("Add LED")
        act_txt = m.addAction("Add Text")
        chosen = m.exec_(ev.globalPos())
        if chosen:
            scene_pos = self.mapToScene(ev.pos())
            if chosen == act_btn:
                self.add_item_at("UIButton", scene_pos.x(), scene_pos.y())
            elif chosen == act_led:
                self.add_item_at("UILed", scene_pos.x(), scene_pos.y())
            elif chosen == act_txt:
                self.add_item_at("UIText", scene_pos.x(), scene_pos.y())
