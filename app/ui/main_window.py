from PyQt5 import QtWidgets, QtCore, QtGui
from .graph import GraphScene, GraphView, NodeItem, TYPE_COLORS, CommentItem
from ..core.registry import registry
from ..core.engine import ExecutionEngine
from ..core.engine_async import EngineRunner
from .variables_panel import VariablesPanel
# register nodes
from ..nodes import math as math_nodes  # noqa: F401
from ..nodes import control as control_nodes  # noqa: F401
from ..nodes import convert as convert_nodes  # noqa: F401
from ..nodes import variables_runtime as variable_nodes  # noqa: F401
from ..nodes.variables_runtime import _cast as cast_var

DTYPE_MAP = {'String': str, 'Int': int, 'Float': float, 'Bool': bool}

class LegendWidget(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        layout = QtWidgets.QFormLayout(self)
        layout.setContentsMargins(8,8,8,8)
        for typ, color in [
            ("bool", TYPE_COLORS[bool]),
            ("int", TYPE_COLORS[int]),
            ("float", TYPE_COLORS[float]),
            ("string", TYPE_COLORS[str]),
            ("tuple/vector", TYPE_COLORS[tuple]),
            ("object", TYPE_COLORS[object]),
            ("exec (flow)", QtGui.QColor("#FFFFFF")),
        ]:
            sw = QtWidgets.QFrame(); sw.setFixedSize(18,18)
            sw.setStyleSheet(f"background-color: {color.name()}; border: 1px solid #222;")
            layout.addRow(sw, QtWidgets.QLabel(typ))

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PyQt5 Node Editor – Starter (v6.4)")

        self.scene = GraphScene(self)
        self.view = GraphView(self.scene)
        self.setCentralWidget(self.view)

        self.palette = QtWidgets.QTreeWidget()
        self._fill_palette()
        self.palette.setHeaderHidden(True)
        self.paletteDock = QtWidgets.QDockWidget("Palette", self)
        self.paletteDock.setWidget(self.palette)
        self.addDockWidget(QtCore.Qt.LeftDockWidgetArea, self.paletteDock)

        # Variables panel (Blueprint-style)
        self.varsPanel = VariablesPanel(self)
        self.varsDock = QtWidgets.QDockWidget("Variables", self)
        self.varsDock.setWidget(self.varsPanel)
        self.addDockWidget(QtCore.Qt.LeftDockWidgetArea, self.varsDock)
        # Create nodes from variables via panel
        self.varsPanel.addGetRequested.connect(self._spawn_get_variable)
        self.varsPanel.addSetRequested.connect(self._spawn_set_variable)
        # react to variable edits
        self.varsPanel.variableRenamed.connect(self._on_var_renamed)
        self.varsPanel.variableTypeChanged.connect(self._on_var_type_changed)
        self.varsPanel.variableRemoved.connect(self._on_var_removed)
        self.varsPanel.variableAdded.connect(self._on_var_added)
        self.varsPanel.variableInitChanged.connect(self._on_var_init_changed)
        self.var_defs = {}

        self.palette.itemDoubleClicked.connect(self._add_from_palette)

        self.legendDock = QtWidgets.QDockWidget("Légende des types", self)
        self.legendDock.setWidget(LegendWidget())
        self.addDockWidget(QtCore.Qt.RightDockWidgetArea, self.legendDock)

        self.log = QtWidgets.QPlainTextEdit(); self.log.setReadOnly(True)
        self.logDock = QtWidgets.QDockWidget("Log", self); self.logDock.setWidget(self.log)
        self.addDockWidget(QtCore.Qt.BottomDockWidgetArea, self.logDock)

        tb = self.addToolBar("Main")
        runAct = tb.addAction("Run"); runAct.triggered.connect(self.run_graph)
        stopAct = tb.addAction("Stop"); stopAct.triggered.connect(self.stop_run)
        clearAct = tb.addAction("Clear"); clearAct.triggered.connect(self.clear_graph)
        addCommentAct = tb.addAction("Commentaire"); addCommentAct.triggered.connect(self.add_comment_here)

        # Context menu (right-click on view)
        self.view.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.view.customContextMenuRequested.connect(self._context_menu)

        # --- EngineRunner (background execution) ---
        self.engine_runner = EngineRunner(self)
        self._hooks = MainWindow.Hooks(self)
        self.engine_runner.sigNodeStarted.connect(self._hooks.on_node_start)
        self.engine_runner.sigNodeFinished.connect(self._hooks.on_node_finish)
        self.engine_runner.sigEdgeFired.connect(self._hooks.on_edge_fired)
        self.engine_runner.sigNodeOutput.connect(self._hooks.on_node_output)
        self.engine_runner.sigRunStarted.connect(lambda: self.log.appendPlainText("--- RUN (async) ---"))
        self.engine_runner.sigRunFinished.connect(self._on_engine_finished)
        self.engine_runner.sigError.connect(lambda msg: self.log.appendPlainText(f"[ERREUR] {msg}"))

        self._example_graph()

    def _fill_palette(self):
        self.palette.clear()
        cats = registry.by_category()
        for cat, classes in cats.items():
            cat_item = QtWidgets.QTreeWidgetItem([cat])
            self.palette.addTopLevelItem(cat_item)
            for cls in classes:
                leaf = QtWidgets.QTreeWidgetItem([cls.type_name()])
                leaf.setData(0, QtCore.Qt.UserRole, cls.type_name())
                cat_item.addChild(leaf)
        self.palette.expandAll()


    def _add_from_palette(self, item):
        pos = self.view.mapToScene(self.view.viewport().rect().center())
        name = item.data(0, QtCore.Qt.UserRole)
        if not name:
            return  # clicked on a category
        self.scene.add_node(name, pos)



    def _context_menu(self, pos):
        gpos = self.view.mapToGlobal(pos)
        menu = QtWidgets.QMenu(self)
        addMenu = menu.addMenu("Ajouter noeud")
        cats = registry.by_category()
        for cat, classes in cats.items():
            sub = addMenu.addMenu(cat)
            for cls in classes:
                act = sub.addAction(cls.type_name())
                act.triggered.connect(lambda _, tt=cls.type_name(): self.add_node_at_cursor(tt, gpos))
        menu.addAction("Ajouter commentaire", lambda: self.add_comment_here(gpos))

        sel = self.scene.selectedItems()
        for it in sel:
            if isinstance(it, CommentItem):
                menu.addAction("Changer la couleur du commentaire", lambda it=it: self.change_comment_color(it))
                break

        menu.exec_(gpos)

    def change_comment_color(self, comment_item):
        color = QtWidgets.QColorDialog.getColor(comment_item.color, self, "Couleur du commentaire")
        if color.isValid():
            comment_item.setColor(color)

    def add_comment_here(self, gpos=None):
        if gpos is None:
            pos = self.view.mapToScene(self.view.viewport().rect().center())
        else:
            pos = self.view.mapToScene(self.view.mapFromGlobal(gpos))
        self.scene.add_comment(pos)

    def add_node_at_cursor(self, type_name: str, gpos):
        pos = self.view.mapToScene(self.view.mapFromGlobal(gpos))
        self.scene.add_node(type_name, pos)

    def clear_graph(self):
        self.scene.clear()
        self.scene.nodes.clear()
        self.scene.edges.clear()
        if hasattr(self.scene, "comments"):
            self.scene.comments.clear()

    class Hooks:
        def __init__(self, mw: "MainWindow"):
            self.mw = mw
        def on_node_start(self, nid: str):
            self.mw.scene.set_node_active(nid, True)
        def on_node_finish(self, nid: str):
            self.mw.scene.set_node_active(nid, False)
        def on_edge_fired(self, src_id: str, src_port: str, dst_id: str, dst_port: str):
            self.mw.scene.mark_exec_edge(src_id, src_port, dst_id, dst_port)
        def on_node_output(self, nid: str, out: dict):
            if out and "printed" in out:
                from datetime import datetime
                ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
                self.mw.log.appendPlainText(f"[{ts}] {out['printed']}")

    def run_graph(self):
        nodes, edges = self.scene.build_specs()
        try:
            init_vars = {name: val for name, (t, val) in self.var_defs.items()}
            self.engine_runner.start(nodes, edges, init_vars)
        except Exception as e:
            self.log.appendPlainText(f"[ERREUR] {e}")
    
    def _on_engine_finished(self, results: dict):
        # Affiche les impressions 'Print' à la fin d'un run async
        text_lines = []
        for nid, out in (results or {}).items():
            if out and "printed" in out:
                text_lines.append(f"{nid} (Print): {out['printed']}")
        if not text_lines:
            text_lines.append("(aucune sortie 'Print')")
        self.log.appendPlainText("\n".join(text_lines))

    # ----- variables sync -----
    def _iter_var_nodes(self, name: str):
        for item in self.scene.nodes.values():
            if item.type_name in ("GetVariable", "SetVariable") and item._params.get("name") == name:
                yield item

    def _apply_variable_style(self, item: NodeItem, name: str, tname: str, dtype: type, error: bool = False):
        item._params['name'] = name
        item._params['type'] = tname
        item._params['_port_types'] = {'value': dtype}
        if item.subtitle_item:
            item.subtitle_item.setText(name)
        port = item.outputs.get('value') if item.type_name == "GetVariable" else item.inputs.get('value')
        if port:
            port.dtype = dtype
            port._update_appearance()
        if item.type_name == "GetVariable":
            ed = item.output_editors.pop('value', None)
            if ed:
                item.scene().removeItem(ed)
        if error:
            brush = QtGui.QBrush(QtGui.QColor('#AA0000'), QtCore.Qt.DiagCrossPattern)
            item._missing_var = True
        else:
            brush = QtGui.QBrush(TYPE_COLORS.get(dtype, TYPE_COLORS[object]))
            item._missing_var = False
        item.header.setBrush(brush)

    def _on_var_added(self, name: str, tname: str, init_val: str):
        val = cast_var(init_val, tname)
        self.var_defs[name] = (tname, val)
        dtype = DTYPE_MAP.get(tname, str)
        for item in self._iter_var_nodes(name):
            # only relink nodes that were previously missing and of same type
            if getattr(item, '_missing_var', False) and item._params.get('type') == tname:
                self._apply_variable_style(item, name, tname, dtype, error=False)

    def _on_var_removed(self, name: str, tname: str):
        self.var_defs.pop(name, None)
        dtype = DTYPE_MAP.get(tname, str)
        for item in self._iter_var_nodes(name):
            self._apply_variable_style(item, name, tname, dtype, error=True)

    def _on_var_renamed(self, old: str, new: str, tname: str):
        t, val = self.var_defs.pop(old, (tname, cast_var('', tname)))
        self.var_defs[new] = (tname, val)
        dtype = DTYPE_MAP.get(tname, str)
        for item in self._iter_var_nodes(old):
            self._apply_variable_style(item, new, tname, dtype, error=False)

    def _on_var_type_changed(self, name: str, old_t: str, new_t: str):
        val = self.var_defs.get(name, (old_t, cast_var('', old_t)))[1]
        casted = cast_var(val, new_t)
        self.var_defs[name] = (new_t, casted)
        dtype = DTYPE_MAP.get(new_t, str)
        for item in self._iter_var_nodes(name):
            # update type and color regardless of previous state
            self._apply_variable_style(item, name, new_t, dtype, error=False)
            port = item.outputs.get('value') if item.type_name == "GetVariable" else item.inputs.get('value')
            if port:
                for e in list(port.edges):
                    other = e.dst_port if e.src_port == port else e.src_port
                    if other:
                        other.remove_edge(e)
                    for cp in list(e.control_points):
                        self.scene.removeItem(cp)
                    if e in self.scene.edges:
                        self.scene.edges.remove(e)
                    self.scene.removeItem(e)
                    port.remove_edge(e)

    def _on_var_init_changed(self, name: str, new_val: str):
        if name not in self.var_defs:
            return
        tname, _ = self.var_defs[name]
        self.var_defs[name] = (tname, cast_var(new_val, tname))

    def _spawn_get_variable(self, name: str, tname: str):
        pos = self.view.mapToScene(self.view.viewport().rect().center())
        dtype = DTYPE_MAP.get(tname, str)
        params = {'name': name, 'type': tname, '_port_types': {'value': dtype}, 'subtitle': name}
        item = self.scene.add_node("GetVariable", pos, params=params)
        item.header.setBrush(QtGui.QBrush(TYPE_COLORS[dtype]))
        ed = item.output_editors.pop('value', None)
        if ed:
            self.scene.removeItem(ed)

    def _spawn_set_variable(self, name: str, tname: str):
        pos = self.view.mapToScene(self.view.viewport().rect().center())
        dtype = DTYPE_MAP.get(tname, str)
        params = {'name': name, 'type': tname, '_port_types': {'value': dtype}, 'subtitle': name}
        item = self.scene.add_node("SetVariable", pos, params=params)
        item.header.setBrush(QtGui.QBrush(TYPE_COLORS[dtype]))



    def _example_graph(self):
        center = self.view.mapToScene(self.view.viewport().rect().center())
        self.scene.add_node("BeginPlay", center + QtCore.QPointF(-350, -100))
        self.scene.add_node("Add", center + QtCore.QPointF(0, 60))
        self.scene.add_node("Print", center + QtCore.QPointF(320, 60))


    def stop_run(self):
        try:
            if hasattr(self, "engine_runner") and self.engine_runner is not None:
                self.engine_runner.stop()
                self.log.appendPlainText("[INFO] Arrêt demandé (Stop).")
        except Exception as e:
            self.log.appendPlainText(f"[ERREUR] Stop: {e}")
