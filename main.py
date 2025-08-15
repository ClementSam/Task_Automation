import sys, os
if __package__ is None or __package__ == '':
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
    from app.ui.main_window import MainWindow
else:
    from .ui.main_window import MainWindow
from PyQt5 import QtWidgets

def main():
    app = QtWidgets.QApplication(sys.argv)
    win = MainWindow()
    win.resize(1400, 900)
    win.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
