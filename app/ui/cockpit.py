
from __future__ import annotations
from typing import Dict, Optional
from PyQt5 import QtWidgets, QtGui, QtCore

GRID_SIZE = 24

class LedWidget(QtWidgets.QWidget):
    def __init__(self, color_on="#39d353", color_off="#3a3f44", parent=None):
        super().__init__(parent)
        self.setFixedSize(40, 40)
        self._on = False
        self._color_on = QtGui.QColor(color_on)
        self._color_off = QtGui.QColor(color_off)

    def setOn(self, on: bool, color: Optional[str] = None):
        self._on = bool(on)
        if color:
            self._color_on = QtGui.QColor(color)
        self.update()

    def isOn(self) -> bool:
        return self._on

    def colorOn(self) -> QtGui.QColor: return self._color_on
    def colorOff(self) -> QtGui.QColor: return self._color_off
    def setColorOn(self, c: QtGui.QColor): self._color_on = c; self.update()
    def setColorOff(self, c: QtGui.QColor): self._color_off = c; self.update()

    def paintEvent(self, e: QtGui.QPaintEvent):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing, True)
        rect = self.rect().adjusted(6, 6, -6, -6)
        # base shadow
        p.setPen(QtCore.Qt.NoPen)
        p.setBrush(QtGui.QBrush(QtGui.QColor(0,0,0,160)))
        p.drawEllipse(rect.adjusted(2,2,2,2))
        # led
        col = self._color_on if self._on else self._color_off
        p.setBrush(col)
        p.drawEllipse(rect)
        # halo
        if self._on:
            grad = QtGui.QRadialGradient(rect.center(), rect.width())
            grad.setColorAt(0.0, QtGui.QColor(col.red(), col.green(), col.blue(), 180))
            grad.setColorAt(1.0, QtGui.QColor(col.red(), col.green(), col.blue(), 0))
            p.setBrush(grad)
            p.drawEllipse(rect.adjusted(-6,-6,6,6))


class EditableLabel(QtWidgets.QLabel):
    textEdited = QtCore.pyqtSignal(str)

    def mouseDoubleClickEvent(self, e: QtGui.QMouseEvent):
        txt, ok = QtWidgets.QInputDialog.getText(self, "Éditer", "Texte:", text=self.text())
        if ok:
            self.setText(txt)
            self.textEdited.emit(txt)

class TitleBar(QtWidgets.QFrame):
    renameRequested = QtCore.pyqtSignal()
    copyIdRequested = QtCore.pyqtSignal()
    deleteRequested = QtCore.pyqtSignal()

    def __init__(self, label_text: str):
        super().__init__()
        self.setFixedHeight(18)
        self.setCursor(QtCore.Qt.SizeAllCursor)
        self.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.setStyleSheet("QFrame { background: #404552; color: white; border-radius: 4px; } QLabel { padding-left: 6px; }")
        lay = QtWidgets.QHBoxLayout(self)
        lay.setContentsMargins(6,0,6,0)
        self.lbl = QtWidgets.QLabel(label_text)
        self.lbl.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        lay.addWidget(self.lbl)
        self._drag_pos = None

    def setText(self, txt: str):
        self.lbl.setText(txt)

    def _proxy(self) -> Optional[QtWidgets.QGraphicsProxyWidget]:
        w: QtWidgets.QWidget = self
        proxy = None
        # climb up to find the proxy that embeds this widget
        while w and proxy is None:
            proxy = w.graphicsProxyWidget()
            w = w.parentWidget()
        return proxy

    def mousePressEvent(self, e: QtGui.QMouseEvent):
        if e.button() == QtCore.Qt.LeftButton:
            self._drag_pos = e.globalPos()
            e.accept()
            return
        super().mousePressEvent(e)

    def mouseMoveEvent(self, e: QtGui.QMouseEvent):
        if self._drag_pos is None:
            super().mouseMoveEvent(e); return
        delta = e.globalPos() - self._drag_pos
        self._drag_pos = e.globalPos()
        proxy = self._proxy()
        if proxy is not None:
            proxy.setPos(proxy.pos() + QtCore.QPointF(delta.x(), delta.y()))
        e.accept()

    def mouseReleaseEvent(self, e: QtGui.QMouseEvent):
        self._drag_pos = None
        super().mouseReleaseEvent(e)

    def contextMenuEvent(self, e: QtGui.QContextMenuEvent):
        m = QtWidgets.QMenu(self)
        m.addAction("Renommer…", self.renameRequested.emit)
        m.addAction("Copier l’ID", self.copyIdRequested.emit)
        m.addSeparator()
        m.addAction("Supprimer", self.deleteRequested.emit)
        m.exec_(e.globalPos())

class DraggableContainer(QtWidgets.QWidget):
    textEdited = QtCore.pyqtSignal(str)  # emit current text
    def __init__(self, id_: str, kind: str, content: QtWidgets.QWidget):
        super().__init__()
        self.id = id_
        self.kind = kind  # 'btn' | 'text' | 'led' | 'label'
        self._content = content
        lay = QtWidgets.QVBoxLayout(self); lay.setContentsMargins(4,4,4,4); lay.setSpacing(4)
        self.bar = TitleBar(id_)
        lay.addWidget(self.bar)
        lay.addWidget(content, 1, QtCore.Qt.AlignCenter if kind == "led" else QtCore.Qt.Alignment(0))
        # propagate edits for text widgets
        if isinstance(content, QtWidgets.QLineEdit):
            content.textEdited.connect(self.textEdited.emit)
        elif isinstance(content, QtWidgets.QTextEdit):
            content.textChanged.connect(lambda: self.textEdited.emit(content.toPlainText()))
        elif isinstance(content, EditableLabel):
            content.textEdited.connect(self.textEdited.emit)

    def setId(self, new_id: str):
        self.id = new_id
        self.bar.setText(new_id)

    def contentWidget(self) -> QtWidgets.QWidget:
        return self._content

class CockpitScene(QtWidgets.QGraphicsScene):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setBackgroundBrush(QtGui.QColor(26,26,32))
        self.setSceneRect(-5000, -5000, 10000, 10000)

    def drawBackground(self, painter: QtGui.QPainter, rect: QtCore.QRectF):
        left = int(rect.left()) - (int(rect.left()) % GRID_SIZE)
        top = int(rect.top()) - (int(rect.top()) % GRID_SIZE)
        lines_light = []
        lines_bold = []
        for x in range(left, int(rect.right()), GRID_SIZE):
            lines_light.append(QtCore.QLineF(x, rect.top(), x, rect.bottom()))
            if (x % (GRID_SIZE*4)) == 0: lines_bold.append(QtCore.QLineF(x, rect.top(), x, rect.bottom()))
        for y in range(top, int(rect.bottom()), GRID_SIZE):
            lines_light.append(QtCore.QLineF(rect.left(), y, rect.right(), y))
            if (y % (GRID_SIZE*4)) == 0: lines_bold.append(QtCore.QLineF(rect.left(), y, rect.right(), y))
        pen_light = QtGui.QPen(QtGui.QColor(255,255,255,22)); pen_bold = QtGui.QPen(QtGui.QColor(255,255,255,55))
        painter.setPen(pen_light); painter.drawLines(lines_light)
        painter.setPen(pen_bold); painter.drawLines(lines_bold)

class CockpitWidget(QtWidgets.QDockWidget):
    buttonClicked = QtCore.pyqtSignal(str)       # id
    textEdited = QtCore.pyqtSignal(str, str)     # id, text

    def __init__(self, parent=None):
        super().__init__("Cockpit", parent)
        self._items: Dict[str, QtWidgets.QGraphicsItem] = {}

        self.toolbar = QtWidgets.QToolBar()
        self.btnAddLed = self.toolbar.addAction("LED")
        self.btnAddBtn = self.toolbar.addAction("Bouton")
        self.btnAddText = self.toolbar.addAction("Texte")
        self.btnAddLabel = self.toolbar.addAction("Label")

        w = QtWidgets.QWidget()
        lay = QtWidgets.QVBoxLayout(w); lay.setContentsMargins(0,0,0,0); lay.setSpacing(4)
        lay.addWidget(self.toolbar)

        self.scene = CockpitScene(self)
        self.view = QtWidgets.QGraphicsView(self.scene)
        self.view.setRenderHint(QtGui.QPainter.Antialiasing, True)
        lay.addWidget(self.view)
        self.setWidget(w)

        self.btnAddLed.triggered.connect(lambda: self.add_led(self._unique_id("led")))
        self.btnAddBtn.triggered.connect(lambda: self.add_button(self._unique_id("btn")))
        self.btnAddText.triggered.connect(lambda: self.add_text(self._unique_id("text")))
        self.btnAddLabel.triggered.connect(lambda: self.add_label(self._unique_id("label")))

    def _unique_id(self, prefix: str) -> str:
        i = 1
        while f"{prefix}:{i}" in self._items:
            i += 1
        return f"{prefix}:{i}"

    # ---- API ----
    def _install_container_menu(self, container: DraggableContainer):
        container.bar.renameRequested.connect(lambda: self._rename_item(container.id))
        container.bar.copyIdRequested.connect(lambda: QtWidgets.QApplication.clipboard().setText(container.id))
        container.bar.deleteRequested.connect(lambda: self.remove(container.id))
        container.textEdited.connect(lambda text, cid=container.id: self.textEdited.emit(cid, text))

    def add_led(self, id: str, pos: Optional[QtCore.QPointF]=None, color_on="#39d353", color_off="#3a3f44") -> QtWidgets.QGraphicsProxyWidget:
        if id in self._items: return self._items[id]
        if pos is None: pos = self.view.mapToScene(self.view.viewport().rect().center())
        led = LedWidget(color_on=color_on, color_off=color_off)
        cont = DraggableContainer(id, "led", led)
        proxy = QtWidgets.QGraphicsProxyWidget()
        proxy.setWidget(cont)
        proxy.setFlags(QtWidgets.QGraphicsItem.ItemIsMovable | QtWidgets.QGraphicsItem.ItemIsSelectable)
        proxy.setPos(pos)
        self.scene.addItem(proxy)
        self._items[id] = proxy
        self._install_container_menu(cont)
        return proxy

    def add_button(self, id: str, pos: Optional[QtCore.QPointF]=None, text="Push") -> QtWidgets.QGraphicsProxyWidget:
        if id in self._items: return self._items[id]
        if pos is None: pos = self.view.mapToScene(self.view.viewport().rect().center())
        btn = QtWidgets.QPushButton(text)
        cont = DraggableContainer(id, "btn", btn)
        proxy = QtWidgets.QGraphicsProxyWidget()
        proxy.setWidget(cont)
        proxy.setFlags(QtWidgets.QGraphicsItem.ItemIsMovable | QtWidgets.QGraphicsItem.ItemIsSelectable)
        proxy.setPos(pos)
        self.scene.addItem(proxy)
        self._items[id] = proxy
        btn.clicked.connect(lambda _=False, i=id: self.buttonClicked.emit(i))
        self._install_container_menu(cont)
        return proxy

    def add_text(self, id: str, pos: Optional[QtCore.QPointF]=None, multiline=False, placeholder="") -> QtWidgets.QGraphicsProxyWidget:
        if id in self._items: return self._items[id]
        if pos is None: pos = self.view.mapToScene(self.view.viewport().rect().center())
        widget = QtWidgets.QTextEdit() if multiline else QtWidgets.QLineEdit()
        if hasattr(widget, "setPlaceholderText"):
            widget.setPlaceholderText(placeholder)
        cont = DraggableContainer(id, "text", widget)
        proxy = QtWidgets.QGraphicsProxyWidget()
        proxy.setWidget(cont)
        proxy.setFlags(QtWidgets.QGraphicsItem.ItemIsMovable | QtWidgets.QGraphicsItem.ItemIsSelectable)
        proxy.setPos(pos)
        self.scene.addItem(proxy)
        self._items[id] = proxy
        self._install_container_menu(cont)
        return proxy

    def add_label(self, id: str, pos: Optional[QtCore.QPointF]=None, text: str="Label") -> QtWidgets.QGraphicsProxyWidget:
        if id in self._items: return self._items[id]
        if pos is None: pos = self.view.mapToScene(self.view.viewport().rect().center())
        lbl = EditableLabel(text)
        cont = DraggableContainer(id, "label", lbl)
        proxy = QtWidgets.QGraphicsProxyWidget()
        proxy.setWidget(cont)
        proxy.setFlags(QtWidgets.QGraphicsItem.ItemIsMovable | QtWidgets.QGraphicsItem.ItemIsSelectable)
        proxy.setPos(pos)
        self.scene.addItem(proxy)
        self._items[id] = proxy
        self._install_container_menu(cont)
        return proxy

    def _rename_item(self, old_id: str):
        it = self._items.get(old_id)
        if not it: return
        new_id, ok = QtWidgets.QInputDialog.getText(self, "Renommer l'élément", "Nouvel ID :", text=old_id)
        if not ok or not new_id or new_id == old_id: return
        if new_id in self._items:
            QtWidgets.QMessageBox.warning(self, "Conflit", f"L'ID '{new_id}' existe déjà."); return
        self._items[new_id] = it
        self._items.pop(old_id, None)
        w = it.widget()
        if isinstance(w, DraggableContainer):
            w.setId(new_id)

    def remove(self, id: str) -> None:
        it = self._items.pop(id, None)
        if it:
            self.scene.removeItem(it); it = None

    def _proxy_content(self, proxy: QtWidgets.QGraphicsProxyWidget):
        w = proxy.widget()
        if isinstance(w, DraggableContainer):
            return w.kind, w.contentWidget()
        return None, w

    @QtCore.pyqtSlot(str, bool, object)
    def set_led(self, id: str, on: bool, color):
        it = self._items.get(id)
        if isinstance(it, QtWidgets.QGraphicsProxyWidget):
            kind, w = self._proxy_content(it)
            if kind == "led" and isinstance(w, LedWidget):
                w.setOn(on, color if isinstance(color, str) else None)

    @QtCore.pyqtSlot(str, object, bool, bool)
    def apply_text_action(self, id: str, text, clear: bool, append: bool):
        it = self._items.get(id)
        if isinstance(it, QtWidgets.QGraphicsProxyWidget):
            kind, w = self._proxy_content(it)
            if isinstance(w, QtWidgets.QLineEdit):
                if clear: w.clear()
                elif append: w.setText(w.text() + (str(text) if text is not None else ""))
                else: w.setText("" if text is None else str(text))
            elif isinstance(w, QtWidgets.QTextEdit):
                if clear: w.clear()
                elif append: w.setPlainText(w.toPlainText() + (str(text) if text is not None else ""))
                else: w.setPlainText("" if text is None else str(text))

    def serialize(self) -> Dict:
        out = {"elements": []}
        for id_, it in self._items.items():
            pos = [float(it.pos().x()), float(it.pos().y())]
            if isinstance(it, QtWidgets.QGraphicsProxyWidget):
                kind, w = self._proxy_content(it)
                if kind == "btn" and isinstance(w, QtWidgets.QPushButton):
                    out["elements"].append({"type":"btn","id":id_,"pos":pos,"props":{"text":w.text()}})
                elif kind == "text":
                    if isinstance(w, QtWidgets.QLineEdit):
                        out["elements"].append({"type":"text","id":id_,"pos":pos,"props":{"multiline":False,"text":w.text()}})
                    elif isinstance(w, QtWidgets.QTextEdit):
                        out["elements"].append({"type":"text","id":id_,"pos":pos,"props":{"multiline":True,"text":w.toPlainText()}})
                elif kind == "led" and isinstance(w, LedWidget):
                    out["elements"].append({
                        "type": "led",
                        "id": id_,
                        "pos": pos,
                        "props": {
                            "color_on": w.colorOn().name(),
                            "color_off": w.colorOff().name(),
                            "on": w.isOn(),
                        },
                    })
                elif kind == "label" and isinstance(w, QtWidgets.QLabel):
                    out["elements"].append({"type": "label", "id": id_, "pos": pos, "props": {"text": w.text()}})
        return out

    def deserialize(self, data: Dict) -> None:
        self.clear()
        self._items.clear()
        for el in (data or {}).get("elements", []):
            t = el.get("type")
            id_ = el.get("id","")
            pos = QtCore.QPointF(*el.get("pos",[0,0]))
            props = el.get("props",{})
            if t == "led":
                proxy = self.add_led(id_, pos, color_on=props.get("color_on","#39d353"), color_off=props.get("color_off","#3a3f44"))
                it = self._items.get(id_)
                if isinstance(it, QtWidgets.QGraphicsProxyWidget):
                    kind, w = self._proxy_content(it)
                    if kind == "led" and isinstance(w, LedWidget):
                        w.setOn(bool(props.get("on", False)))
            elif t == "btn":
                self.add_button(id_, pos, text=props.get("text","Push"))
            elif t == "text":
                proxy = self.add_text(id_, pos, multiline=bool(props.get("multiline", False)))
                it = self._items.get(id_)
                if isinstance(it, QtWidgets.QGraphicsProxyWidget):
                    kind, w = self._proxy_content(it)
                    txt = props.get("text","")
                    if isinstance(w, QtWidgets.QLineEdit):
                        w.setText(txt)
                    elif isinstance(w, QtWidgets.QTextEdit):
                        w.setPlainText(txt)
            elif t == "label":
                proxy = self.add_label(id_, pos, text=props.get("text", ""))
