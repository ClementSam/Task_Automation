import os

import pytest

QtWidgets = pytest.importorskip("PyQt5.QtWidgets")


def test_file_logger_writes(tmp_path):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    app = QtWidgets.QApplication.instance()
    created = False
    if app is None:
        app = QtWidgets.QApplication([])
        created = True

    from app.ui.main_window import FileLogger

    log_path = tmp_path / "log.txt"
    fl = FileLogger(log_path)
    fl.appendPlainText("hello")
    fl.close()

    assert log_path.read_text().strip() == "hello"

    if created:
        app.quit()

