from PyQt5 import QtWidgets, QtGui, QtCore
from typing import Dict, List, Tuple, Optional
from ..core.engine import NodeSpec, EdgeSpec, DEFAULT_PREFIX
from ..core.registry import registry

def _new_id():
    _new_id.counter += 1
    return f"n{_new_id.counter}"
_new_id.counter = 0

GRID_SIZE = 24
SNAP_TO_GRID = True

TYPE_COLORS = {
    bool: QtGui.QColor("#98C379"),
    int: QtGui.QColor("#E06C75"),
    float: QtGui.QColor("#2BB1FF"),
    str: QtGui.QColor("#C678DD"),
    tuple: QtGui.QColor("#D19A66"),
    object: QtGui.QColor("#ABB2BF"),
}
EXEC_COLOR = QtGui.QColor("#FFFFFF")
FLOW_COLOR = QtGui.QColor("#FF9A00")

def is_compatible(src_t, dst_t) -> bool:
    return src_t == dst_t

PORT_RADIUS = 6
EXEC_PORT_RADIUS = 7
NODE_W = 300
NODE_H = 140
HEADER_H = 24
PORT_MARGIN = 24

class ControlPointItem(QtWidgets.QGraphicsEllipseItem):
    def __init__(self, edge: "EdgeItem", pos: QtCore.QPointF):
        super().__init__(-5, -5, 10, 10)
        self.edge = edge
        self.setBrush(QtGui.QBrush(QtGui.QColor(220,180,80)))
        self.setPen(QtGui.QPen(QtCore.Qt.black, 1))
        self.setFlags(
            QtWidgets.QGraphicsItem.ItemIsMovable |
            QtWidgets.QGraphicsItem.ItemIsSelectable |
            QtWidgets.QGraphicsItem.ItemSendsGeometryChanges
        )
        # Ensure control points remain above edges and nodes
        self.setZValue(2)
        self.setPos(pos)

    def itemChange(self, change, value):
        if change in (QtWidgets.QGraphicsItem.ItemPositionChange, QtWidgets.QGraphicsItem.ItemPositionHasChanged):
            self.edge.update_path()
        return super().itemChange(change, value)

    def mouseDoubleClickEvent(self, event):
        if self in self.edge.control_points:
            self.edge.control_points.remove(self)
            self.edge.scene().removeItem(self)
            self.edge.update_path()
        super().mouseDoubleClickEvent(event)

class InputLabelItem(QtWidgets.QGraphicsSimpleTextItem):
    def __init__(self, node_item: "NodeItem", name: str, dtype: type):
        super().__init__(name, node_item)
        self.node_item = node_item
        self.input_name = name
        self.dtype = dtype
        self.setBrush(QtGui.QBrush(QtGui.QColor(220,220,220)))

class InputEditor(QtWidgets.QGraphicsProxyWidget):
    def __init__(self, node_item: "NodeItem", name: str, dtype: type):
        super().__init__(node_item)
        self.node_item = node_item
        self.input_name = name
        self.dtype = dtype
        self.setZValue(2)

        if dtype is int:
            w = QtWidgets.QSpinBox(); w.setRange(-10**9, 10**9)
        elif dtype is float:
            w = QtWidgets.QDoubleSpinBox(); w.setDecimals(6); w.setRange(-1e12, 1e12); w.setSingleStep(0.1)
        elif dtype is bool:
            w = QtWidgets.QCheckBox()
        else:
            w = QtWidgets.QLineEdit(); w.setPlaceholderText("valeur...")

        self.widget = w
        self.widget.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.setWidget(w)
        self.setAcceptedMouseButtons(QtCore.Qt.AllButtons)
        self.setFlag(QtWidgets.QGraphicsItem.ItemIsFocusable, True)

        key = DEFAULT_PREFIX + name
        if dtype is bool:
            self.widget.setChecked(bool(self.node_item._params.get(key, False)))
            self.widget.stateChanged.connect(self._on_change)
        else:
            val = self.node_item._params.get(key, "" if dtype is str else 0)
            if isinstance(self.widget, QtWidgets.QLineEdit):
                self.widget.setText(str(val))
                self.widget.textChanged.connect(self._on_change)
            elif isinstance(self.widget, QtWidgets.QSpinBox):
                self.widget.setValue(int(val) if val != "" else 0)
                self.widget.valueChanged.connect(self._on_change)
            elif isinstance(self.widget, QtWidgets.QDoubleSpinBox):
                try: self.widget.setValue(float(val))
                except Exception: self.widget.setValue(0.0)
                self.widget.valueChanged.connect(self._on_change)

    def _on_change(self, *args):
        if self.dtype is bool:
            self.node_item._params[DEFAULT_PREFIX + self.input_name] = bool(self.widget.isChecked())
        elif isinstance(self.widget, QtWidgets.QLineEdit):
            self.node_item._params[DEFAULT_PREFIX + self.input_name] = self.widget.text()
        elif isinstance(self.widget, QtWidgets.QSpinBox):
            self.node_item._params[DEFAULT_PREFIX + self.input_name] = int(self.widget.value())
        elif isinstance(self.widget, QtWidgets.QDoubleSpinBox):
            self.node_item._params[DEFAULT_PREFIX + self.input_name] = float(self.widget.value())

class OutputEditor(QtWidgets.QGraphicsProxyWidget):
    def __init__(self, node_item: "NodeItem", out_name: str, dtype: type):
        super().__init__(node_item)
        self.node_item = node_item
        self.out_name = out_name
        self.dtype = dtype
        self.setZValue(2)

        if dtype is int:
            w = QtWidgets.QSpinBox(); w.setRange(-10**9, 10**9)
        elif dtype is float:
            w = QtWidgets.QDoubleSpinBox(); w.setDecimals(6); w.setRange(-1e12, 1e12); w.setSingleStep(0.1)
        elif dtype is bool:
            w = QtWidgets.QCheckBox()
        else:
            w = QtWidgets.QLineEdit()

        self.widget = w
        self.widget.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.setWidget(w)
        self.setAcceptedMouseButtons(QtCore.Qt.AllButtons)
        self.setFlag(QtWidgets.QGraphicsItem.ItemIsFocusable, True)

        param_key = "value" if out_name == "value" else f"out:{out_name}"
        self.param_key = param_key
        val = self.node_item._params.get(param_key, "" if dtype is str else (False if dtype is bool else 0))
        if dtype is bool:
            self.widget.setChecked(bool(val))
            self.widget.stateChanged.connect(self._on_change)
        elif isinstance(self.widget, QtWidgets.QLineEdit):
            self.widget.setText(str(val))
            self.widget.textChanged.connect(self._on_change)
        elif isinstance(self.widget, QtWidgets.QSpinBox):
            self.widget.setValue(int(val) if val != "" else 0)
            self.widget.valueChanged.connect(self._on_change)
        elif isinstance(self.widget, QtWidgets.QDoubleSpinBox):
            try: self.widget.setValue(float(val))
            except Exception: self.widget.setValue(0.0)
            self.widget.valueChanged.connect(self._on_change)

    def _on_change(self, *args):
        if self.dtype is bool:
            self.node_item._params[self.param_key] = bool(self.widget.isChecked())
        elif isinstance(self.widget, QtWidgets.QLineEdit):
            self.node_item._params[self.param_key] = self.widget.text()
        elif isinstance(self.widget, QtWidgets.QSpinBox):
            self.node_item._params[self.param_key] = int(self.widget.value())
        elif isinstance(self.widget, QtWidgets.QDoubleSpinBox):
            self.node_item._params[self.param_key] = float(self.widget.value())

class PortItem(QtWidgets.QGraphicsEllipseItem):
    def __init__(self, name: str, is_output: bool, parent_node: "NodeItem", kind: str, dtype: type = object):
        r = EXEC_PORT_RADIUS if kind == "exec" else PORT_RADIUS
        super().__init__(-r, -r, 2*r, 2*r, parent_node)
        self.kind = kind
        self.dtype = dtype
        self.name = name
        self.is_output = is_output
        self.parent_node = parent_node
        self.edges: List["EdgeItem"] = []
        self.setFlag(QtWidgets.QGraphicsItem.ItemSendsScenePositionChanges, True)
        self.setAcceptHoverEvents(True)
        self._update_appearance()

    def _update_appearance(self):
        if self.kind == "exec":
            self.setBrush(QtGui.QBrush(EXEC_COLOR))
        else:
            color = TYPE_COLORS.get(self.dtype, TYPE_COLORS[object])
            self.setBrush(QtGui.QBrush(color))
        self.setPen(QtGui.QPen(QtCore.Qt.black, 1))
        self.setToolTip(f'{"out" if self.is_output else "in"} {self.kind}: {self.name}')

    def center_in_scene(self) -> QtCore.QPointF:
        return self.mapToScene(QtCore.QPointF(0,0))

    def add_edge(self, e: "EdgeItem"):
        if e not in self.edges:
            self.edges.append(e)
        self.parent_node.refresh_inline_editors()

    def remove_edge(self, e: "EdgeItem"):
        if e in self.edges:
            self.edges.remove(e)
        self.parent_node.refresh_inline_editors()

    def hoverEnterEvent(self, e):
        self.setScale(1.1)
        super().hoverEnterEvent(e)

    def hoverLeaveEvent(self, e):
        self.setScale(1.0)
        super().hoverLeaveEvent(e)

    def itemChange(self, change, value):
        if change == QtWidgets.QGraphicsItem.ItemScenePositionHasChanged:
            for e in list(self.edges):
                e.update_path()
        return super().itemChange(change, value)

class EdgeItem(QtWidgets.QGraphicsPathItem):
    def __init__(self, kind: str, src_port: PortItem, dst_port: PortItem = None):
        super().__init__()
        # Draw edges above nodes for better visibility
        self.setZValue(1)
        self.kind = kind
        self.src_port = src_port
        self.dst_port = dst_port
        self.control_points: List[ControlPointItem] = []
        self.setFlags(QtWidgets.QGraphicsItem.ItemIsSelectable)
        self.flow_active = False
        self.flow_phase = 0.0
        self.flow_ttl = 0
        self._reset_pen()
        self.update_path()

    def _reset_pen(self):
        pen = QtGui.QPen(QtCore.Qt.black, 2)
        if self.kind == "exec":
            pen.setColor(EXEC_COLOR); pen.setWidth(3)
        else:
            color = TYPE_COLORS.get(self.src_port.dtype, TYPE_COLORS[object]); pen.setColor(color)
        pen.setCapStyle(QtCore.Qt.RoundCap)
        self.setPen(pen)

    def start_flow(self, duration_ms=600):
        self.flow_active = True
        self.flow_ttl = max(self.flow_ttl, duration_ms // 30)
        pen = QtGui.QPen(FLOW_COLOR, 4)
        pen.setDashPattern([6, 8])
        pen.setDashOffset(self.flow_phase)
        pen.setCapStyle(QtCore.Qt.RoundCap)
        self.setPen(pen)

    def tick_flow(self):
        if not self.flow_active: return
        self.flow_phase += 1.5
        pen = self.pen(); pen.setDashOffset(self.flow_phase); self.setPen(pen)
        self.flow_ttl -= 1
        if self.flow_ttl <= 0:
            self.flow_active = False
            self._reset_pen()

    def update_path(self, end_pos: QtCore.QPointF = None):
        p = QtGui.QPainterPath()
        src = self.src_port.center_in_scene()
        dst = self.dst_port.center_in_scene() if self.dst_port is not None else (end_pos or self.src_port.center_in_scene())
        points = [src] + [cp.scenePos() for cp in self.control_points] + [dst]
        p.moveTo(points[0])
        for i in range(1, len(points)):
            a = points[i-1]; b = points[i]
            dx = abs(b.x() - a.x())
            c1 = QtCore.QPointF(a.x() + max(60, dx*0.3), a.y())
            c2 = QtCore.QPointF(b.x() - max(60, dx*0.3), b.y())
            p.cubicTo(c1, c2, b)
        self.setPath(p)

    def mouseDoubleClickEvent(self, event):
        cp = ControlPointItem(self, event.scenePos())
        self.scene().addItem(cp)
        self.control_points.append(cp)
        self.update_path()
        super().mouseDoubleClickEvent(event)

class NodeItem(QtWidgets.QGraphicsObject):
    def __init__(self, node_id: str, type_name: str, params=None):
        super().__init__()
        self.node_id = node_id
        self.type_name = type_name
        self._params = params or {}
        self.active = False

        # child visuals
        self.bg = QtWidgets.QGraphicsRectItem(0, 0, NODE_W, NODE_H, self)
        self.bg.setBrush(QtGui.QBrush(QtGui.QColor(50,50,60)))
        self.bg.setPen(QtGui.QPen(QtGui.QColor(80,80,100), 1))

        self.header = QtWidgets.QGraphicsRectItem(0, 0, NODE_W, HEADER_H, self)
        # header color set later based on node type
        self.header.setBrush(QtGui.QBrush(QtGui.QColor(70,70,90)))
        self.header.setPen(QtGui.QPen(QtCore.Qt.NoPen))

        node_cls = registry.types()[type_name]
        title = node_cls.title()
        if getattr(node_cls, 'event_node', False):
            self.header.setBrush(QtGui.QBrush(QtGui.QColor('#C0392B')))
        self.title_item = QtWidgets.QGraphicsSimpleTextItem(title, self)
        # optional subtitle (e.g., variable name)
        subtitle = self._params.get('subtitle') if isinstance(self._params, dict) else None
        if subtitle:
            self.subtitle_item = QtWidgets.QGraphicsSimpleTextItem(str(subtitle), self)
            self.subtitle_item.setBrush(QtGui.QBrush(QtGui.QColor(200,200,210)))
            f2 = self.subtitle_item.font(); f2.setPointSize(8); self.subtitle_item.setFont(f2)
        else:
            self.subtitle_item = None
        self.title_item.setBrush(QtGui.QBrush(QtGui.QColor(230,230,230)))
        self.title_item.setPos(8, 4)
        if self.subtitle_item:
            self.subtitle_item.setPos(8, 22)

        self.setFlags(
            QtWidgets.QGraphicsItem.ItemIsMovable |
            QtWidgets.QGraphicsItem.ItemIsSelectable |
            QtWidgets.QGraphicsItem.ItemSendsGeometryChanges
        )
        self.setAcceptHoverEvents(True)

        self.inputs: Dict[str, PortItem] = {}
        self.outputs: Dict[str, PortItem] = {}
        self.exec_inputs: Dict[str, PortItem] = {}
        self.exec_outputs: Dict[str, PortItem] = {}
        self.input_labels: Dict[str, InputLabelItem] = {}
        self.input_editors: Dict[str, InputEditor] = {}
        self.output_editors: Dict[str, OutputEditor] = {}

        self._build_ports_and_editors()

    # QGraphicsObject requires boundingRect/paint
    def boundingRect(self):
        return QtCore.QRectF(0,0,NODE_W,NODE_H)

    def paint(self, painter, option, widget=None):
        pass

    def _build_ports_and_editors(self):
        node_cls = registry.types()[self.type_name]
        ins = list(node_cls.inputs().items())
        outs = list(node_cls.outputs().items())
        ein = list(node_cls.exec_inputs())
        eout = list(node_cls.exec_outputs())

        y_exec = HEADER_H + 6
        for name in ein:
            p = PortItem(name, is_output=False, parent_node=self, kind="exec")
            p.setPos(0, y_exec)
            self.exec_inputs[name] = p
            y_exec += 16
        y_exec = HEADER_H + 6
        for name in eout:
            p = PortItem(name, is_output=True, parent_node=self, kind="exec")
            p.setPos(NODE_W, y_exec)
            self.exec_outputs[name] = p
            y_exec += 16

        y = HEADER_H + PORT_MARGIN
        for name, dtype in ins:
            p = PortItem(name, is_output=False, parent_node=self, kind="data", dtype=dtype)
            p.setPos(0, y)
            lbl = InputLabelItem(self, name, dtype); lbl.setPos(10, y-8)
            self.inputs[name] = p; self.input_labels[name] = lbl
            ed = InputEditor(self, name, dtype); ed.setPos(95, y-14); ed.widget.setFixedWidth(140)
            self.input_editors[name] = ed
            y += PORT_MARGIN

        y = HEADER_H + PORT_MARGIN
        for name, dtype in outs:
            p = PortItem(name, is_output=True, parent_node=self, kind="data", dtype=dtype)
            p.setPos(NODE_W, y)
            txt = QtWidgets.QGraphicsSimpleTextItem(name, self)
            txt.setBrush(QtGui.QBrush(QtGui.QColor(220,220,220)))
            w = txt.boundingRect().width(); txt.setPos(NODE_W - w - 18, y-8)
            self.outputs[name] = p
            if not ins:
                out_ed = OutputEditor(self, name, dtype)
                out_ed.setPos(NODE_W - 170, y-14); out_ed.widget.setFixedWidth(150)
                self.output_editors[name] = out_ed
            y += PORT_MARGIN

        self.refresh_inline_editors()

    def refresh_inline_editors(self):
        for name, ed in self.input_editors.items():
            wired = len(self.inputs[name].edges) > 0
            ed.setVisible(not wired)
        for name, ed in self.output_editors.items():
            ed.setVisible(True)
        # Apply instance port type overrides
        pt = self._params.get('_port_types') if isinstance(self._params, dict) else None
        if pt:
            for name, dtype in pt.items():
                if name in self.outputs:
                    self.outputs[name].dtype = dtype
                    self.outputs[name]._update_appearance()
                if name in self.inputs:
                    self.inputs[name].dtype = dtype
                    self.inputs[name]._update_appearance()

    def params(self) -> dict:
        return dict(self._params)

    def setActive(self, flag: bool):
        self.active = flag
        pen = QtGui.QPen(QtGui.QColor("#FF9A00") if flag else QtGui.QColor(80,80,100), 2 if flag else 1)
        self.bg.setPen(pen)

    def itemChange(self, change, value):
        if change in (QtWidgets.QGraphicsItem.ItemPositionChange, QtWidgets.QGraphicsItem.ItemPositionHasChanged):
            if SNAP_TO_GRID and change == QtWidgets.QGraphicsItem.ItemPositionChange:
                pos = value
                x = round(pos.x() / GRID_SIZE) * GRID_SIZE
                y = round(pos.y() / GRID_SIZE) * GRID_SIZE
                return QtCore.QPointF(x, y)
            for port in list(self.inputs.values()) + list(self.outputs.values()) + list(self.exec_inputs.values()) + list(self.exec_outputs.values()):
                for e in list(port.edges):
                    e.update_path()
        return super().itemChange(change, value)

class EditableTextItem(QtWidgets.QGraphicsTextItem):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setDefaultTextColor(QtGui.QColor(230,230,230))
        self.setTextInteractionFlags(QtCore.Qt.NoTextInteraction)

    def mouseDoubleClickEvent(self, event):
        self.setTextInteractionFlags(QtCore.Qt.TextEditorInteraction)
        self.setFocus(QtCore.Qt.MouseFocusReason)
        super().mouseDoubleClickEvent(event)

    def focusOutEvent(self, event):
        self.setTextInteractionFlags(QtCore.Qt.NoTextInteraction)
        super().focusOutEvent(event)

class ResizerHandle(QtWidgets.QGraphicsRectItem):
    SIZE = 10
    def __init__(self, parent_comment: "CommentItem", corner: str):
        super().__init__(-ResizerHandle.SIZE/2, -ResizerHandle.SIZE/2, ResizerHandle.SIZE, ResizerHandle.SIZE, parent_comment)
        self.parent_comment = parent_comment
        self.corner = corner
        self.setBrush(QtGui.QBrush(QtGui.QColor(220,220,220)))
        self.setPen(QtGui.QPen(QtCore.Qt.black, 1))
        self.setFlags(QtWidgets.QGraphicsItem.ItemIsMovable | QtWidgets.QGraphicsItem.ItemSendsGeometryChanges)
        curs = {"tl": QtCore.Qt.SizeFDiagCursor, "br": QtCore.Qt.SizeFDiagCursor, "tr": QtCore.Qt.SizeBDiagCursor, "bl": QtCore.Qt.SizeBDiagCursor}[corner]
        self.setCursor(curs)
        self.setZValue(-1)

    def itemChange(self, change, value):
        if change == QtWidgets.QGraphicsItem.ItemPositionChange:
            if getattr(self.parent_comment, "_updating_handles", False):
                return super().itemChange(change, value)
            pos = self.mapToParent(value)
            if SNAP_TO_GRID:
                pos = QtCore.QPointF(round(pos.x()/GRID_SIZE)*GRID_SIZE, round(pos.y()/GRID_SIZE)*GRID_SIZE)
            self.parent_comment.resize_from_handle(self.corner, pos)
            return self.mapFromParent(pos)
        return super().itemChange(change, value)

class CommentItem(QtWidgets.QGraphicsItemGroup):
    def __init__(self, rect: QtCore.QRectF, color: QtGui.QColor):
        super().__init__()
        self.rect = rect
        self._updating_handles = False
        self.rect_item = QtWidgets.QGraphicsRectItem(rect, self)
        self.color = color
        brush = QtGui.QBrush(color); brush.setColor(QtGui.QColor(color.red(), color.green(), color.blue(), 60))
        self.rect_item.setBrush(brush)
        self.rect_item.setPen(QtGui.QPen(color, 2, QtCore.Qt.DashLine))
        self.addToGroup(self.rect_item)

        self.label = EditableTextItem("Commentaire", self)
        self.label.setPos(rect.topLeft() + QtCore.QPointF(8, 4))
        self.addToGroup(self.label)

        self.h_tl = ResizerHandle(self, "tl")
        self.h_tr = ResizerHandle(self, "tr")
        self.h_bl = ResizerHandle(self, "bl")
        self.h_br = ResizerHandle(self, "br")
        self._update_handles()

        self.setFlags(QtWidgets.QGraphicsItem.ItemIsMovable | QtWidgets.QGraphicsItem.ItemIsSelectable | QtWidgets.QGraphicsItem.ItemSendsGeometryChanges)
        self.setZValue(-2)

    def setColor(self, color: QtGui.QColor):
        self.color = color
        brush = QtGui.QBrush(color); brush.setColor(QtGui.QColor(color.red(), color.green(), color.blue(), 60))
        self.rect_item.setBrush(brush)
        self.rect_item.setPen(QtGui.QPen(color, 2, QtCore.Qt.DashLine))

    def resize_from_handle(self, corner: str, new_pos_in_parent: QtCore.QPointF):
        if self._updating_handles:
            return
        r = QtCore.QRectF(self.rect)
        if corner == "tl": r.setTopLeft(new_pos_in_parent)
        elif corner == "tr": r.setTopRight(new_pos_in_parent)
        elif corner == "bl": r.setBottomLeft(new_pos_in_parent)
        elif corner == "br": r.setBottomRight(new_pos_in_parent)
        if r.width() < 80: r.setWidth(80)
        if r.height() < 60: r.setHeight(60)
        if SNAP_TO_GRID:
            x = round(r.x()/GRID_SIZE)*GRID_SIZE; y = round(r.y()/GRID_SIZE)*GRID_SIZE
            w = round(r.width()/GRID_SIZE)*GRID_SIZE; h = round(r.height()/GRID_SIZE)*GRID_SIZE
            r = QtCore.QRectF(x, y, max(GRID_SIZE, w), max(GRID_SIZE, h))
        self.rect = r; self.rect_item.setRect(r); self.label.setPos(r.topLeft() + QtCore.QPointF(8, 4)); self._update_handles()

    def _update_handles(self):
        self._updating_handles = True
        r = self.rect_item.rect()
        self.h_tl.setPos(r.topLeft())
        self.h_tr.setPos(r.topRight())
        self.h_bl.setPos(r.bottomLeft())
        self.h_br.setPos(r.bottomRight())
        self._updating_handles = False

    def itemChange(self, change, value):
        if change == QtWidgets.QGraphicsItem.ItemPositionChange and SNAP_TO_GRID:
            pos = value
            x = round(pos.x() / GRID_SIZE) * GRID_SIZE
            y = round(pos.y() / GRID_SIZE) * GRID_SIZE
            return QtCore.QPointF(x, y)
        return super().itemChange(change, value)

class GraphScene(QtWidgets.QGraphicsScene):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setBackgroundBrush(QtGui.QBrush(QtGui.QColor(30,30,36)))
        self.setSceneRect(-5000, -5000, 10000, 10000)
        self.nodes: Dict[str, NodeItem] = {}
        self.edges: List[EdgeItem] = []
        self.comments: List[CommentItem] = []

        self._temp_edge: Optional[EdgeItem] = None
        self._temp_src_port: Optional[PortItem] = None

        self._timer = QtCore.QTimer(); self._timer.timeout.connect(self._on_tick); self._timer.start(30)

    def _on_tick(self):
        for e in list(self.edges): e.tick_flow()

    def set_node_active(self, nid: str, flag: bool):
        node = self.nodes.get(nid)
        if node: node.setActive(flag)

    def mark_exec_edge(self, src_id: str, src_port: str, dst_id: str, dst_port: str):
        for e in self.edges:
            if e.kind != "exec": continue
            if (e.src_port.parent_node.node_id == src_id and e.src_port.name == src_port and e.dst_port.parent_node.node_id == dst_id and e.dst_port.name == dst_port):
                e.start_flow()

    def add_node(self, type_name: str, pos: QtCore.QPointF, params: dict=None) -> NodeItem:
        nid = _new_id()
        item = NodeItem(nid, type_name, params=params)
        self.addItem(item)
        item.setPos(pos - QtCore.QPointF(NODE_W/2, NODE_H/2))
        self.nodes[nid] = item
        return item

    def add_comment(self, pos: QtCore.QPointF, color: QtGui.QColor = QtGui.QColor("#4CAF50")):
        rect = QtCore.QRectF(pos.x(), pos.y(), 300, 200)
        c = CommentItem(rect, color)
        self.addItem(c); self.comments.append(c)
        return c

    def mousePressEvent(self, event):
        # When edges are drawn above nodes they can intercept clicks intended
        # for ports. Retrieve the item under the cursor but skip edges so
        # that ports remain clickable even if covered by a path.
        items = self.items(event.scenePos())
        item = None
        for it in items:
            if not isinstance(it, (EdgeItem, ControlPointItem)):
                item = it
                break
        if item is None and items:
            item = items[0]

        if isinstance(item, PortItem):
            if item.is_output and event.button() == QtCore.Qt.LeftButton:
                self._temp_src_port = item; self._temp_edge = EdgeItem(kind=item.kind, src_port=item); self.addItem(self._temp_edge); event.accept(); return
            elif (not item.is_output) and self._temp_edge is not None:
                if self._temp_src_port is not None and item.parent_node != self._temp_src_port.parent_node:
                    if self._is_link_allowed(self._temp_src_port, item):
                        e = self._finalize_edge(self._temp_src_port, item);
                        if e: self.edges.append(e)
                self._cancel_temp(); event.accept(); return
        super().mousePressEvent(event)

    def _is_link_allowed(self, src: PortItem, dst: PortItem) -> bool:
        if src.kind != dst.kind: return False
        if dst.is_output or src.is_output is False: return False
        for e in list(dst.edges):
            self.removeItem(e); dst.remove_edge(e)
            if e.src_port: e.src_port.remove_edge(e)
            if e in self.edges: self.edges.remove(e)
        if src.kind == "data": return is_compatible(src.dtype, dst.dtype)
        return True

    def mouseMoveEvent(self, event):
        if self._temp_edge is not None:
            self._temp_edge.update_path(end_pos=event.scenePos()); event.accept(); return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self._temp_edge is not None and event.button() == QtCore.Qt.RightButton:
            self._cancel_temp(); event.accept(); return
        super().mouseReleaseEvent(event)

    def _cancel_temp(self):
        if self._temp_edge is not None:
            self.removeItem(self._temp_edge); self._temp_edge = None
        self._temp_src_port = None

    def _finalize_edge(self, src_port: PortItem, dst_port: PortItem):
        e = EdgeItem(kind=src_port.kind, src_port=src_port, dst_port=dst_port)
        self.addItem(e); src_port.add_edge(e); dst_port.add_edge(e); e.update_path(); return e

    def delete_selected(self):
        for item in list(self.selectedItems()):
            if isinstance(item, EdgeItem):
                if item in self.edges: self.edges.remove(item)
                if item.src_port: item.src_port.remove_edge(item)
                if item.dst_port: item.dst_port.remove_edge(item)
                for cp in list(item.control_points): self.removeItem(cp)
                self.removeItem(item)
            elif isinstance(item, NodeItem):
                for port in list(item.inputs.values()) + list(item.outputs.values()) + list(item.exec_inputs.values()) + list(item.exec_outputs.values()):
                    for e in list(port.edges):
                        if e in self.edges: self.edges.remove(e)
                        if e.src_port: e.src_port.remove_edge(e)
                        if e.dst_port: e.dst_port.remove_edge(e)
                        for cp in list(e.control_points): self.removeItem(cp)
                        self.removeItem(e)
                if item.node_id in self.nodes: del self.nodes[item.node_id]
                self.removeItem(item)
            elif isinstance(item, CommentItem):
                if item in self.comments: self.comments.remove(item)
                self.removeItem(item)

    def build_specs(self) -> Tuple[List[NodeSpec], List[EdgeSpec]]:
        nodes = []; edges = []
        for nid, item in self.nodes.items():
            nodes.append(NodeSpec(id=nid, type_name=item.type_name, params=item.params()))
        for e in self.edges:
            if e.src_port is None or e.dst_port is None: continue
            edges.append(EdgeSpec(kind=e.kind, src_id=e.src_port.parent_node.node_id, src_port=e.src_port.name, dst_id=e.dst_port.parent_node.node_id, dst_port=e.dst_port.name))
        return nodes, edges

class GraphView(QtWidgets.QGraphicsView):
    def __init__(self, scene: GraphScene):
        super().__init__(scene)
        self.setRenderHints(QtGui.QPainter.Antialiasing | QtGui.QPainter.TextAntialiasing | QtGui.QPainter.SmoothPixmapTransform)
        self.setDragMode(QtWidgets.QGraphicsView.RubberBandDrag)
        self.setViewportUpdateMode(QtWidgets.QGraphicsView.FullViewportUpdate)
        self.setTransformationAnchor(QtWidgets.QGraphicsView.AnchorUnderMouse)

    def wheelEvent(self, event):
        self.scale(1.25 if event.angleDelta().y() > 0 else 0.8, 1.25 if event.angleDelta().y() > 0 else 0.8)

    def drawBackground(self, painter: QtGui.QPainter, rect: QtCore.QRectF):
        super().drawBackground(painter, rect)
        left = int(rect.left()) - (int(rect.left()) % GRID_SIZE)
        top = int(rect.top()) - (int(rect.top()) % GRID_SIZE)
        lines_light = []; lines_bold = []
        for x in range(left, int(rect.right()), GRID_SIZE):
            lines_light.append(QtCore.QLineF(x, rect.top(), x, rect.bottom()))
            if (x % (GRID_SIZE*4)) == 0: lines_bold.append(QtCore.QLineF(x, rect.top(), x, rect.bottom()))
        for y in range(top, int(rect.bottom()), GRID_SIZE):
            lines_light.append(QtCore.QLineF(rect.left(), y, rect.right(), y))
            if (y % (GRID_SIZE*4)) == 0: lines_bold.append(QtCore.QLineF(rect.left(), y, rect.right(), y))
        pen_light = QtGui.QPen(QtGui.QColor(255,255,255,30)); pen_bold = QtGui.QPen(QtGui.QColor(255,255,255,60))
        painter.setPen(pen_light); painter.drawLines(lines_light)
        painter.setPen(pen_bold); painter.drawLines(lines_bold)

    def keyPressEvent(self, event):
        if event.key() in (QtCore.Qt.Key_Delete,):
            self.scene().delete_selected(); event.accept(); return
        super().keyPressEvent(event)
