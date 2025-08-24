import os
import pytest

QtWidgets = pytest.importorskip("PyQt5.QtWidgets")


def _setup_qt():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QtWidgets.QApplication.instance()
    created = False
    if app is None:
        app = QtWidgets.QApplication([])
        created = True
    return app, created


def test_cockpit_save_load_led_and_label():
    app, created = _setup_qt()
    from app.ui.cockpit import CockpitWidget, LedWidget

    c1 = CockpitWidget()
    c1.add_led("led:1")
    c1.set_led("led:1", True, None)
    c1.add_label("label:1", text="Hello")

    data = c1.serialize()

    c2 = CockpitWidget()
    c2.deserialize(data)

    led_proxy = c2._items["led:1"]
    _, led_widget = c2._proxy_content(led_proxy)
    assert isinstance(led_widget, LedWidget)
    assert led_widget.isOn()

    label_proxy = c2._items["label:1"]
    _, label_widget = c2._proxy_content(label_proxy)
    assert isinstance(label_widget, QtWidgets.QLabel)
    assert label_widget.text() == "Hello"

    if created:
        app.quit()


def test_cockpit_delete_selected():
    app, created = _setup_qt()
    from app.ui.cockpit import CockpitWidget

    c = CockpitWidget()
    c.add_button("btn:1")
    proxy = c._items["btn:1"]
    proxy.setSelected(True)
    c.delete_selected()
    assert "btn:1" not in c._items

    if created:
        app.quit()


def test_cockpit_title_edit_allows_deletion():
    app, created = _setup_qt()
    from app.ui.cockpit import CockpitWidget
    from PyQt5 import QtCore, QtGui

    c = CockpitWidget()
    c.add_button("btn:1")
    proxy = c._items["btn:1"]
    container = proxy.widget()
    title_edit = container.bar.lbl

    title_edit.setText("abc")
    title_edit.setFocus()

    # send a backspace key event through the view; the title should update
    event = QtGui.QKeyEvent(QtCore.QEvent.KeyPress, QtCore.Qt.Key_Backspace, QtCore.Qt.NoModifier)
    QtWidgets.QApplication.sendEvent(c.view, event)

    assert title_edit.text() == "ab"
    assert "btn:1" in c._items

    if created:
        app.quit()

