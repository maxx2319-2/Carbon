import multiprocessing
import sys
import importlib
import threading

from PySide6.QtCore import QEvent, QEventLoop, QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QPainter, QPixmap, QIcon
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QApplication, QSplashScreen, QProgressBar

from path import resource_path


class CarbonApp(QApplication):
    def __init__(self, argv):
        super().__init__(argv)
        self.window = None
        self.pending_file = None

    def event(self, event):
        if event.type() == QEvent.FileOpen and event.file().endswith(".crbn"):
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
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)
        self.setWindowTitle("Carbon")
        self.setWindowIcon(QIcon(str(resource_path("Assets/Carbon_Round.svg"))))
        self.bar = QProgressBar(self)
        self.bar.setGeometry(40, 192, 340, 8)
        self.bar.setTextVisible(False)
        self.bar.setStyleSheet("QProgressBar { background: #323232; border: none; border-radius: 4px; } QProgressBar::chunk { background: white; border-radius: 4px; }")

    def progress(self, value):
        self.bar.setValue(int(value))
        QApplication.processEvents()

    def status(self, text):
        self.showMessage(text, Qt.AlignBottom | Qt.AlignHCenter, QColor("#b4b4b4"))

    def mousePressEvent(self, event):
        pass

if __name__ == "__main__":
    multiprocessing.freeze_support()
    QApplication.setAttribute(Qt.AA_ShareOpenGLContexts)
    app = CarbonApp(sys.argv)
    app.setWindowIcon(QIcon(str(resource_path("Assets/Carbon_Round.svg"))))
    splash = Splash(app)
    splash.show()
    modules = ["pandas", "sympy", "scipy.optimize", "matplotlib.pyplot"]
    done = []

    def load():
        for name in modules:
            importlib.import_module(name)
            done.append(name)

    def tick():
        if not loader.is_alive():
            loop.quit()
        cap = 50 * (len(done) + 1) // len(modules) - 1
        splash.bar.setValue(max(50 * len(done) // len(modules), min(splash.bar.value() + 1, cap)))
        splash.status(f"Indlæser {list(sys.modules)[-1]}")

    loader = threading.Thread(target=load, daemon=True)
    loop = QEventLoop()
    timer = QTimer(interval=50)
    timer.timeout.connect(tick)
    loader.start()
    timer.start()
    loop.exec()
    timer.stop()
    splash.status("Indlæser Carbon")
    import gui
    splash.progress(50)
    gui.main(app, splash)