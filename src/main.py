import multiprocessing
import sys
import importlib

from PySide6.QtCore import QEvent, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QApplication, QSplashScreen, QProgressBar

from path import resource_path


class CarbonApp(QApplication):
    def __init__(self, argv):
        super().__init__(argv)
        self.window = None
        self.pending_file = None

    def event(self, event):
        if event.type() == QEvent.FileOpen:
            if self.window:
                self.window.load_regneark(event.file())
            else:
                self.pending_file = event.file()
            return True
        return super().event(event)

class Splash(QSplashScreen):
    def __init__(self, app):
        ratio = app.primaryScreen().devicePixelRatio()
        pixmap = QPixmap(int(420 * ratio), int(220 * ratio))
        pixmap.setDevicePixelRatio(ratio)
        pixmap.fill(QColor("#404040"))
        painter = QPainter(pixmap)
        QSvgRenderer(str(resource_path("Assets/Carbon_Full.svg"))).render(painter, QRectF(30, 15, 360, 160))
        painter.end()
        super().__init__(pixmap)
        self.bar = QProgressBar(self)
        self.bar.setGeometry(40, 192, 340, 8)
        self.bar.setTextVisible(False)
        self.bar.setStyleSheet("QProgressBar { background: #323232; border: none; border-radius: 4px; } QProgressBar::chunk { background: white; border-radius: 4px; }")

    def progress(self, value):
        self.bar.setValue(int(value))
        QApplication.processEvents()

if __name__ == "__main__":
    multiprocessing.freeze_support()
    QApplication.setAttribute(Qt.AA_ShareOpenGLContexts)
    app = CarbonApp(sys.argv)
    splash = Splash(app)
    splash.show()
    splash.progress(0)
    modules = ["quantity", "utils", "matplotlib.pyplot", "scipy.linalg", "chem", "interpreter", "gui"]
    for i, name in enumerate(modules, 1):
        importlib.import_module(name)
        splash.progress(50 * i / len(modules))
    import gui
    gui.main(app, splash)