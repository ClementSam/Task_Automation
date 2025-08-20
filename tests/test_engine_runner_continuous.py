from PyQt5 import QtCore

from app.core.engine_async import EngineRunner


def _app():
    app = QtCore.QCoreApplication.instance()
    if app is None:
        app = QtCore.QCoreApplication([])
    return app


def test_engine_runner_continuous_mode_applied_before_start():
    _app()  # ensure a Qt application exists
    runner = EngineRunner()
    runner.setContinuousRun(True)
    runner.start([], [])
    assert runner._scheduler is not None
    assert runner._scheduler.is_continuous_run() is True
    runner.setContinuousRun(False)
    assert runner._scheduler.is_continuous_run() is False
