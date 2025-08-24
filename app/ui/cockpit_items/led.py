
from PyQt5 import QtWidgets, QtGui, QtCore
from ...core.cockpit_registry import cockpit_registry
from .base import CockpitGraphicsItem

class LedWidget(QtWidgets.QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._on = False
        self._color = QtGui.QColor('green')
        self.setFixedSize(22, 22)

    def set_state(self, on: bool, color):
        self._on = bool(on)
        if color is not None:
            try:
                self._color = QtGui.QColor(color)
            except Exception:
                pass
        self.update()

    def paintEvent(self, ev):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing, True)
        r = self.rect().adjusted(2,2,-2,-2)
        p.setPen(QtCore.Qt.NoPen)
        if self._on:
            p.setBrush(QtGui.QBrush(self._color))
        else:
            c = QtGui.QColor(self._color)
            c.setAlpha(80)
            p.setBrush(QtGui.QBrush(c))
        p.drawEllipse(r)

@cockpit_registry.register("UILed")
class CockpitLedItem(CockpitGraphicsItem):
    def __init__(self, scheduler, model):
        super().__init__(scheduler, model)
        self._led = LedWidget()
        self.set_header_widget(self._led)

    def set_led(self, on: bool, color):
        self._led.set_state(on, color)
