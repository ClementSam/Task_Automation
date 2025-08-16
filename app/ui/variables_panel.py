
from PyQt5 import QtWidgets, QtCore

_TYPES = ['String', 'Int', 'Float', 'Bool']


def _cast(val: str, tname: str) -> str:
    typemap = {'String': str, 'Int': int, 'Float': float, 'Bool': bool}
    typ = typemap.get(tname, str)
    try:
        if typ is bool:
            if isinstance(val, str):
                return str(val).lower() in ('1', 'true', 'yes', 'on')
            return bool(val)
        return typ(val)
    except Exception:
        return typ()


class VariablesPanel(QtWidgets.QWidget):
    addGetRequested = QtCore.pyqtSignal(str, str)  # (name, type)
    addSetRequested = QtCore.pyqtSignal(str, str)
    variableRenamed = QtCore.pyqtSignal(str, str, str)  # old_name, new_name, type
    variableTypeChanged = QtCore.pyqtSignal(str, str, str)  # name, old_type, new_type
    variableRemoved = QtCore.pyqtSignal(str, str)  # name, type
    variableAdded = QtCore.pyqtSignal(str, str, str)  # name, type, init_value
    variableInitChanged = QtCore.pyqtSignal(str, str)  # name, new_init_value

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)

        # Toolbar
        tb = QtWidgets.QToolBar(self)
        self.actAdd = tb.addAction('+')
        self.actRemove = tb.addAction('-')
        layout.addWidget(tb)

        # Table with action buttons column
        self.table = QtWidgets.QTableWidget(0, 4, self)
        self.table.setHorizontalHeaderLabels(['Name', 'Type', 'Init Value', ''])
        self.table.horizontalHeader().setStretchLastSection(False)
        self.table.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QtWidgets.QHeaderView.ResizeToContents)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.DoubleClicked | QtWidgets.QAbstractItemView.SelectedClicked)
        layout.addWidget(self.table)

        # Optional context menu for additional actions
        self.table.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._menu)

        self.table.itemChanged.connect(self._on_item_changed)
        self._var_data = {}

        self.actAdd.triggered.connect(self._add_row)
        self.actRemove.triggered.connect(self._remove_selected)

    def variables(self):
        out = []
        for r in range(self.table.rowCount()):
            name_item = self.table.item(r, 0)
            combo = self.table.cellWidget(r, 1)
            init_item = self.table.item(r, 2)
            name = name_item.text().strip() if name_item else ''
            t = combo.currentText() if combo else 'String'
            init_val = init_item.text().strip() if init_item else ''
            if name:
                out.append((name, t, init_val))
        return out

    def _row_from_widget(self, w: QtWidgets.QWidget) -> int:
        widget = w
        if widget.parent() and widget.parent() is not self.table:
            widget = widget.parent()  # cell widget container
        return self.table.indexAt(widget.pos()).row()

    def _add_row(self, name: str = '', t: str = 'String', init: str = ''):
        r = self.table.rowCount()
        self.table.insertRow(r)
        name_item = QtWidgets.QTableWidgetItem(name)
        self.table.setItem(r, 0, name_item)

        combo = QtWidgets.QComboBox()
        combo.addItems(_TYPES)
        combo.setCurrentText(t)
        combo.currentTextChanged.connect(lambda nt, c=combo: self._on_type_changed(c, nt))
        self.table.setCellWidget(r, 1, combo)

        init_val = str(_cast(init, t))
        init_item = QtWidgets.QTableWidgetItem(init_val)
        self.table.setItem(r, 2, init_item)

        # action buttons
        w = QtWidgets.QWidget()
        lay = QtWidgets.QHBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(2)
        bget = QtWidgets.QToolButton(); bget.setText('Get')
        bset = QtWidgets.QToolButton(); bset.setText('Set')
        lay.addWidget(bget); lay.addWidget(bset)
        bget.clicked.connect(lambda _, b=bget: self._on_add_get(b))
        bset.clicked.connect(lambda _, b=bset: self._on_add_set(b))
        self.table.setCellWidget(r, 3, w)

        self._var_data[r] = (name, t, init_val)

    def _remove_selected(self):
        rows = sorted({i.row() for i in self.table.selectedIndexes()}, reverse=True)
        for r in rows:
            name_item = self.table.item(r, 0)
            combo = self.table.cellWidget(r, 1)
            name = name_item.text().strip() if name_item else ''
            t = combo.currentText() if combo else 'String'
            if name:
                self.variableRemoved.emit(name, t)
            self.table.removeRow(r)
        self._rebuild_var_data()

    def _on_item_changed(self, item: QtWidgets.QTableWidgetItem):
        r = item.row()
        name_item = self.table.item(r, 0)
        combo = self.table.cellWidget(r, 1)
        init_item = self.table.item(r, 2)
        name = name_item.text().strip() if name_item else ''
        t = combo.currentText() if combo else 'String'
        init_val = init_item.text().strip() if init_item else ''
        old_name, old_type, old_val = self._var_data.get(r, ('', 'String', ''))

        if item.column() == 0:
            if not old_name and name:
                self.variableAdded.emit(name, t, init_val)
            elif old_name != name:
                self.variableRenamed.emit(old_name, name, t)
        elif item.column() == 2:
            self.variableInitChanged.emit(name, init_val)

        self._var_data[r] = (name, t, init_val)

    def _on_type_changed(self, combo: QtWidgets.QComboBox, new_t: str):
        r = self._row_from_widget(combo)
        name_item = self.table.item(r, 0)
        init_item = self.table.item(r, 2)
        name = name_item.text().strip() if name_item else ''
        old_name, old_type, old_val = self._var_data.get(r, ('', 'String', ''))
        casted = str(_cast(init_item.text() if init_item else '', new_t)) if init_item else ''
        if init_item:
            init_item.setText(casted)
        if name:
            if not old_name and name:
                self.variableAdded.emit(name, new_t, casted)
            elif old_type != new_t:
                self.variableTypeChanged.emit(name, old_type, new_t)
                self.variableInitChanged.emit(name, casted)
        self._var_data[r] = (name, new_t, casted)

    def _on_add_get(self, btn: QtWidgets.QToolButton):
        r = self._row_from_widget(btn)
        name_item = self.table.item(r, 0)
        combo = self.table.cellWidget(r, 1)
        name = name_item.text().strip() if name_item else ''
        t = combo.currentText() if combo else 'String'
        if name:
            self.addGetRequested.emit(name, t)

    def _on_add_set(self, btn: QtWidgets.QToolButton):
        r = self._row_from_widget(btn)
        name_item = self.table.item(r, 0)
        combo = self.table.cellWidget(r, 1)
        name = name_item.text().strip() if name_item else ''
        t = combo.currentText() if combo else 'String'
        if name:
            self.addSetRequested.emit(name, t)

    def _rebuild_var_data(self):
        self._var_data = {}
        for r in range(self.table.rowCount()):
            name_item = self.table.item(r, 0)
            combo = self.table.cellWidget(r, 1)
            init_item = self.table.item(r, 2)
            name = name_item.text().strip() if name_item else ''
            t = combo.currentText() if combo else 'String'
            init_val = init_item.text().strip() if init_item else ''
            self._var_data[r] = (name, t, init_val)

    def _menu(self, gpos):
        idx = self.table.indexAt(gpos)
        if not idx.isValid():
            return
        r = idx.row()
        name = self.table.item(r, 0).text().strip()
        combo = self.table.cellWidget(r, 1)
        t = combo.currentText() if combo else 'String'
        m = QtWidgets.QMenu(self)
        m.addAction('Add GET node', lambda: self.addGetRequested.emit(name, t))
        m.addAction('Add SET node', lambda: self.addSetRequested.emit(name, t))
        m.exec_(self.table.viewport().mapToGlobal(gpos))
