import os
import sys

os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = "--disable-gpu"

from PySide6.QtCore import QPoint, Qt, QTimer, QUrl
from PySide6.QtTest import QTest
from PySide6.QtWebEngineCore import QWebEnginePage
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QApplication

page_path = os.path.abspath(sys.argv[1])
script = open(sys.argv[2], encoding="utf-8").read() if len(sys.argv) > 2 and sys.argv[2] != "-" else ""
shot = sys.argv[3] if len(sys.argv) > 3 else None
timeout = int(os.environ.get("TIMEOUT_MS", "60000"))

app = QApplication(sys.argv)
KEYS = {"z": Qt.Key_Z, "1": Qt.Key_1, "2": Qt.Key_2, "enter": Qt.Key_Return}


def act(message):
    kind, arg = message.split(":", 1)
    target = view.focusProxy()
    if kind == "TYPE":
        QTest.keyClicks(target, arg)
    elif kind == "SLOW":
        for ch in arg:
            QTest.keyClicks(target, ch)
            QTest.qWait(60)
    elif kind == "KEY":
        *mods, key = arg.split("+")
        QTest.keyClick(target, KEYS[key], Qt.ControlModifier if "ctrl" in mods else Qt.NoModifier)
    else:
        x, y = (int(float(v)) for v in arg.split(","))
        button = Qt.RightButton if kind == "RCLICK" else Qt.LeftButton
        QTest.mouseMove(target, QPoint(x, y))
        QTest.mousePress(target, button, Qt.NoModifier, QPoint(x, y))
        QTest.mouseRelease(target, button, Qt.NoModifier, QPoint(x, y))
    QTimer.singleShot(400, lambda: page.runJavaScript("window.resume()"))


class Page(QWebEnginePage):
    def javaScriptConsoleMessage(self, level, message, line, source):
        print(message, flush=True)
        if message.split(":", 1)[0] in ("TYPE", "SLOW", "KEY", "RCLICK", "LCLICK"):
            QTimer.singleShot(0, lambda: act(message))
        if message == "DONE":
            if shot:
                QTimer.singleShot(300, finish)
            else:
                app.quit()


def finish():
    view.grab().save(shot)
    app.quit()


view = QWebEngineView()
view.resize(900, 600)
page = Page(view)
view.setPage(page)
page.loadFinished.connect(lambda ok: page.runJavaScript(script) if script else None)
view.load(QUrl.fromLocalFile(page_path))
view.show()
QTimer.singleShot(timeout, lambda: (print("TIMEOUT", flush=True), app.quit()))
app.exec()
