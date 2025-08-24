
from PyQt5 import QtWidgets, QtCore

_TYPES = ['String', 'Int', 'Float', 'Bool', 'SerialPortRef', 'ScopeRef']
_KINDS = ['Normale', 'Tableau']

def _split_type(t: str):
    """Retourne (base_type, is_array) depuis 'Int' ou 'Int[]'."""
    if isinstance(t, str) and t.endswith('[]'):
        return t[:-2], True
    return t, False


def _cast(val: str, tname: str) -> str:
    typemap = {'String': str, 'Int': int, 'Float': float, 'Bool': bool}
    if tname in ('SerialPortRef', 'ScopeRef'):
        return ''
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
        self.table = QtWidgets.QTableWidget(0, 5, self)
        self.table.setHorizontalHeaderLabels(['Name', 'Type', 'Kind', 'Init Value', ''])
        self.table.horizontalHeader().setStretchLastSection(False)
        self.table.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QtWidgets.QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QtWidgets.QHeaderView.ResizeToContents)
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
            type_combo = self.table.cellWidget(r, 1)
            kind_combo = self.table.cellWidget(r, 2)
            init_item = self.table.item(r, 3)
            name = name_item.text().strip() if name_item else ''
            base_t = type_combo.currentText() if type_combo else 'String'
            is_array = (kind_combo.currentText() == 'Tableau') if kind_combo else False
            t = f"{base_t}[]" if is_array else base_t
            init_val = init_item.text().strip() if init_item else ''
            if name:
                out.append((name, t, init_val))
        return out

    def _row_from_widget(self, w: QtWidgets.QWidget) -> int:
        """Return the row index for a widget placed in the table."""
        # Map the widget's position to the table's viewport to reliably find
        # the index, regardless of any intermediate container widgets
        pos_in_viewport = w.mapTo(self.table.viewport(), QtCore.QPoint(0, 0))
        return self.table.indexAt(pos_in_viewport).row()

    def _add_row(self, name: str = '', t: str = 'String', init: str = ''):
        base_t, is_array = _split_type(t)
        r = self.table.rowCount()
        self.table.insertRow(r)
        name_item = QtWidgets.QTableWidgetItem(name)
        self.table.setItem(r, 0, name_item)

        type_combo = QtWidgets.QComboBox(); type_combo.addItems(_TYPES)
        type_combo.setCurrentText(base_t)
        self.table.setCellWidget(r, 1, type_combo)

        kind_combo = QtWidgets.QComboBox(); kind_combo.addItems(_KINDS)
        kind_combo.setCurrentText('Tableau' if is_array else 'Normale')
        self.table.setCellWidget(r, 2, kind_combo)

        init_val = str(_cast(init, base_t)) if not is_array else str(init)
        init_item = QtWidgets.QTableWidgetItem(init_val)
        self.table.setItem(r, 3, init_item)

        # action buttons
        w = QtWidgets.QWidget()
        lay = QtWidgets.QHBoxLayout(w); lay.setContentsMargins(0,0,0,0); lay.setSpacing(2)
        bget = QtWidgets.QToolButton(); bget.setText('Get')
        bset = QtWidgets.QToolButton(); bset.setText('Set')
        lay.addWidget(bget); lay.addWidget(bset)
        self.table.setCellWidget(r, 4, w)

        type_combo.currentTextChanged.connect(lambda _=None, rr=r: self._on_type_or_kind_changed(rr))
        kind_combo.currentTextChanged.connect(lambda _=None, rr=r: self._on_type_or_kind_changed(rr))
        bget.clicked.connect(lambda _, b=bget: self._on_add_get(b))
        bset.clicked.connect(lambda _, b=bset: self._on_add_set(b))

        eff_t = f"{base_t}[]" if is_array else base_t
        self._var_data[r] = (name, eff_t, init_val)

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
        init_item = self.table.item(r, 3)
        name = name_item.text().strip() if name_item else ''
        init_val = init_item.text().strip() if init_item else ''
        type_combo = self.table.cellWidget(r, 1)
        kind_combo = self.table.cellWidget(r, 2)
        base_t = type_combo.currentText() if type_combo else 'String'
        is_array = (kind_combo.currentText() == 'Tableau') if kind_combo else False
        t = f"{base_t}[]" if is_array else base_t
        old_name, old_type, old_val = self._var_data.get(r, ('', 'String', ''))

        if item.column() == 0:
            if not old_name and name:
                self.variableAdded.emit(name, t, init_val)
            elif old_name != name:
                self.variableRenamed.emit(old_name, name, t)
        elif item.column() == 3:
            self.variableInitChanged.emit(name, init_val)

        self._var_data[r] = (name, t, init_val)

    def _on_type_or_kind_changed(self, r: int):
        name_item = self.table.item(r, 0)
        init_item = self.table.item(r, 3)
        name = name_item.text().strip() if name_item else ''
        type_combo = self.table.cellWidget(r, 1)
        kind_combo = self.table.cellWidget(r, 2)
        base_t = type_combo.currentText() if type_combo else 'String'
        is_array = (kind_combo.currentText() == 'Tableau') if kind_combo else False
        new_t = f"{base_t}[]" if is_array else base_t
        old_name, old_type, old_val = self._var_data.get(r, ('', 'String', ''))
        casted = str(_cast(init_item.text() if init_item else '', base_t)) if init_item else ''
        if init_item:
            init_item.setText(casted if not is_array else init_item.text())
        if name:
            if not old_name and name:
                self.variableAdded.emit(name, new_t, casted)
            elif old_type != new_t:
                self.variableTypeChanged.emit(name, old_type, new_t)
                self.variableInitChanged.emit(name, casted if not is_array else init_item.text())
        self._var_data[r] = (name, new_t, casted if not is_array else init_item.text())

    def _on_add_get(self, btn: QtWidgets.QToolButton):
        r = self._row_from_widget(btn)
        name_item = self.table.item(r, 0)
        type_combo = self.table.cellWidget(r, 1)
        kind_combo = self.table.cellWidget(r, 2)
        base_t = type_combo.currentText() if type_combo else 'String'
        is_array = (kind_combo.currentText() == 'Tableau') if kind_combo else False
        t = f"{base_t}[]" if is_array else base_t
        name = name_item.text().strip() if name_item else ''
        if name:
            self.addGetRequested.emit(name, t)

    def _on_add_set(self, btn: QtWidgets.QToolButton):
        r = self._row_from_widget(btn)
        name_item = self.table.item(r, 0)
        type_combo = self.table.cellWidget(r, 1)
        kind_combo = self.table.cellWidget(r, 2)
        base_t = type_combo.currentText() if type_combo else 'String'
        is_array = (kind_combo.currentText() == 'Tableau') if kind_combo else False
        t = f"{base_t}[]" if is_array else base_t
        name = name_item.text().strip() if name_item else ''
        if name:
            self.addSetRequested.emit(name, t)

    def _rebuild_var_data(self):
        self._var_data = {}
        for r in range(self.table.rowCount()):
            name_item = self.table.item(r, 0)
            type_combo = self.table.cellWidget(r, 1)
            kind_combo = self.table.cellWidget(r, 2)
            init_item = self.table.item(r, 3)
            name = name_item.text().strip() if name_item else ''
            base_t = type_combo.currentText() if type_combo else 'String'
            is_array = (kind_combo.currentText() == 'Tableau') if kind_combo else False
            t = f"{base_t}[]" if is_array else base_t
            init_val = init_item.text().strip() if init_item else ''
            self._var_data[r] = (name, t, init_val)

    def _menu(self, gpos):
        idx = self.table.indexAt(gpos)
        if not idx.isValid():
            return
        r = idx.row()
        name = self.table.item(r, 0).text().strip()
        type_combo = self.table.cellWidget(r, 1)
        kind_combo = self.table.cellWidget(r, 2)
        base_t = type_combo.currentText() if type_combo else 'String'
        is_array = (kind_combo.currentText() == 'Tableau') if kind_combo else False
        t = f"{base_t}[]" if is_array else base_t
        m = QtWidgets.QMenu(self)
        m.addAction('Add GET node', lambda: self.addGetRequested.emit(name, t))
        m.addAction('Add SET node', lambda: self.addSetRequested.emit(name, t))
        m.exec_(self.table.viewport().mapToGlobal(gpos))