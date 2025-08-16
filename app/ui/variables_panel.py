
from PyQt5 import QtWidgets, QtCore
_TYPES = ['String','Int','Float','Bool']

class VariablesPanel(QtWidgets.QWidget):
    addGetRequested = QtCore.pyqtSignal(str, str)  # (name, type)
    addSetRequested = QtCore.pyqtSignal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QtWidgets.QVBoxLayout(self); layout.setContentsMargins(6,6,6,6); layout.setSpacing(6)

        # Toolbar
        tb = QtWidgets.QToolBar(self)
        self.actAdd = tb.addAction('+'); self.actRemove = tb.addAction('-')
        layout.addWidget(tb)

        # Table
        self.table = QtWidgets.QTableWidget(0, 2, self)
        self.table.setHorizontalHeaderLabels(['Name','Type'])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.DoubleClicked | QtWidgets.QAbstractItemView.SelectedClicked)
        layout.addWidget(self.table)

        # Context menu
        self.table.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._menu)

        self.actAdd.triggered.connect(self._add_row)
        self.actRemove.triggered.connect(self._remove_selected)

    def variables(self):
        out = []
        for r in range(self.table.rowCount()):
            name_item = self.table.item(r, 0)
            type_item = self.table.cellWidget(r, 1)
            name = name_item.text().strip() if name_item else ''
            t = type_item.currentText() if type_item else 'String'
            if name: out.append((name, t))
        return out

    def _add_row(self, name='', t='String'):
        r = self.table.rowCount(); self.table.insertRow(r)
        name_item = QtWidgets.QTableWidgetItem(name); self.table.setItem(r, 0, name_item)
        combo = QtWidgets.QComboBox(); combo.addItems(_TYPES); combo.setCurrentText(t)
        self.table.setCellWidget(r, 1, combo)

    def _remove_selected(self):
        rows = sorted({i.row() for i in self.table.selectedIndexes()}, reverse=True)
        for r in rows: self.table.removeRow(r)

    def _menu(self, gpos):
        idx = self.table.indexAt(gpos)
        if not idx.isValid(): return
        r = idx.row()
        name = self.table.item(r,0).text().strip()
        combo = self.table.cellWidget(r,1)
        t = combo.currentText() if combo else 'String'
        m = QtWidgets.QMenu(self)
        m.addAction('Add GET node', lambda: self.addGetRequested.emit(name, t))
        m.addAction('Add SET node', lambda: self.addSetRequested.emit(name, t))
        m.exec_(self.table.viewport().mapToGlobal(gpos))
