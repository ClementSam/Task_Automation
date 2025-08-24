
from PyQt5 import QtCore, QtWidgets, QtGui

TITLE_H = 28
W, H = 220, 90
MARGIN = 8
HEADER_SLOT_W = 90  # width reserved on the right side of header for control

class CockpitGraphicsItem(QtWidgets.QGraphicsObject):
    renamed = QtCore.pyqtSignal(str)  # new display name

    def __init__(self, scheduler, model):
        super().__init__()
        self.scheduler = scheduler
        self.model = model
        self._w = W
        self._h = H
        self._header_widget = None
        self._body_widget = None

        self.setFlags(self.ItemIsMovable | self.ItemIsSelectable | self.ItemSendsGeometryChanges)

        # Title (editable) — left area
        self.title = QtWidgets.QGraphicsTextItem(self)
        self.title.setPlainText(self.model.display_name or self.model.type_name)
        self.title.setTextInteractionFlags(QtCore.Qt.TextEditorInteraction)
        self.title.setDefaultTextColor(QtGui.QColor(20, 20, 20))
        f = QtGui.QFont()
        f.setBold(False)
        self.title.setFont(f)
        self.title.setZValue(2)

        # Proxies for header-right widget and body widget
        self.headerProxy = QtWidgets.QGraphicsProxyWidget(self)
        self.bodyProxy = QtWidgets.QGraphicsProxyWidget(self)
        self.headerProxy.setZValue(1)
        self.bodyProxy.setZValue(1)

        # Hook rename
        self._orig_focus_out = self.title.focusOutEvent
        self.title.focusOutEvent = self._on_title_edited

        self._relayout()

    # ---- public helpers ---------------------------------------------
    def set_size(self, w: int, h: int):
        self._w = int(w)
        self._h = int(h)
        self._relayout()
        self.update()

    def set_header_widget(self, w: QtWidgets.QWidget):
        self._header_widget = w
        self.headerProxy.setWidget(w)
        # small default height for header
        w.setMinimumHeight(22)
        self._relayout()

    def set_body_widget(self, w: QtWidgets.QWidget):
        self._body_widget = w
        self.bodyProxy.setWidget(w)
        self._relayout()

    def set_widget(self, w: QtWidgets.QWidget):
        # Backward compat: put into body area
        self.set_body_widget(w)

    # ---- internals ---------------------------------------------------
    def _on_title_edited(self, ev):
        try:
            if self._orig_focus_out:
                self._orig_focus_out(ev)
        finally:
            txt = (self.title.toPlainText() or "").strip()
            if txt != self.model.display_name:
                self.model.display_name = txt
                try:
                    self.renamed.emit(txt)
                except Exception:
                    pass

    def _relayout(self):
        # Position title (left margin)
        self.title.setPos(MARGIN, 4)
        self.title.setTextWidth(max(10, self._w - HEADER_SLOT_W - 3*MARGIN))

        # Place header widget at right of header bar
        if self._header_widget:
            hx = self._w - HEADER_SLOT_W - MARGIN + 4
            hy = max(2, (TITLE_H - self._header_widget.sizeHint().height()) // 2)
            self.headerProxy.setPos(hx, hy)
            self._header_widget.setFixedWidth(HEADER_SLOT_W - 8)

        # Place body widget filling the card body
        if self._body_widget:
            bx = MARGIN
            by = TITLE_H + 8
            bw = max(40, self._w - 2*MARGIN)
            bh = max(24, self._h - TITLE_H - 16)
            self.bodyProxy.setPos(bx, by)
            try:
                self._body_widget.setFixedSize(int(bw), int(bh))
            except Exception:
                pass

    # ---- QGraphics API ----------------------------------------------
    def boundingRect(self) -> QtCore.QRectF:
        return QtCore.QRectF(0, 0, self._w, self._h + TITLE_H)

    def paint(self, p: QtGui.QPainter, opt, widget=None):
        r = self.boundingRect()
        p.save()
        # Outer card
        p.setPen(QtGui.QPen(QtGui.QColor(70, 70, 70)))
        p.setBrush(QtGui.QBrush(QtGui.QColor(245, 245, 245)))
        p.drawRoundedRect(r, 6, 6)

        # Title bar
        title_rect = QtCore.QRectF(0, 0, r.width(), TITLE_H)
        p.setPen(QtGui.QPen(QtGui.QColor(200, 200, 200)))
        p.setBrush(QtGui.QBrush(QtGui.QColor(252, 252, 252)))
        p.drawRect(title_rect)

        # Vertical separator between title-left and header control
        sep_x = float(r.width() - HEADER_SLOT_W - 4)
        p.setPen(QtGui.QPen(QtGui.QColor(180, 180, 180)))
        p.drawLine(QtCore.QLineF(sep_x, 0.0, sep_x, float(TITLE_H)))

        # Bottom line of header
        p.drawLine(QtCore.QLineF(0.0, float(TITLE_H), float(r.width()), float(TITLE_H)))

        # Body background
        body_rect = QtCore.QRectF(MARGIN, TITLE_H + 8, r.width() - 2*MARGIN, r.height() - TITLE_H - 16)
        p.setPen(QtGui.QPen(QtGui.QColor(210, 210, 210)))
        p.setBrush(QtGui.QBrush(QtGui.QColor(250, 250, 250)))
        p.drawRect(body_rect)

        p.restore()

    def mouseDoubleClickEvent(self, ev: QtWidgets.QGraphicsSceneMouseEvent):
        # If double-click inside title area, start editing
        if ev.pos().y() <= TITLE_H:
            self.title.setTextInteractionFlags(QtCore.Qt.TextEditorInteraction)
            self.title.setFocus()
        super().mouseDoubleClickEvent(ev)
