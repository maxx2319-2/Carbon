import json
import os
import sys
import tempfile

os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = "--disable-gpu"
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
sys.path.insert(0, os.path.join(ROOT, "src"))

from PySide6.QtCore import QEventLoop, QSettings, QTimer, QUrl
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QApplication


def main():
    app = QApplication(sys.argv)
    import gui

    ini = os.path.join(tempfile.mkdtemp(), "carbon_test.ini")
    gui._settings = QSettings(ini, QSettings.IniFormat)
    gui._settings.setValue("spell_words", json.dumps(["zzyzxchem"]))

    def js(view, code):
        loop, out = QEventLoop(), []
        view.page().runJavaScript(code, 0, lambda r: (out.append(r), loop.quit()))
        loop.exec()
        return out[0]

    def open_page():
        view = QWebEngineView()
        channel = QWebChannel(view.page())
        bridge = gui._InterpreterBridge(view)
        channel.registerObject("bridge", bridge)
        view.page().setWebChannel(channel)
        loop = QEventLoop()
        view.loadFinished.connect(loop.quit)
        view.load(QUrl.fromLocalFile(os.path.abspath(os.path.join(ROOT, "Assets_math_live", "regneark.html"))))
        loop.exec()
        for _ in range(200):
            if js(view, "spell.ready && bridge !== null && spell.ignored.size > 0"):
                break
            QTimer.singleShot(50, lambda: None)
            wait = QEventLoop()
            QTimer.singleShot(50, wait.quit)
            wait.exec()
        js(view, "applyMode(first, 'text'); setLine(first, '\\\\text{zzyzxchem og flubbergast er ord}'); true")
        return view, bridge

    view, bridge = open_page()
    print("1 word from settings loaded:", js(view, "spell.ignored.has('zzyzxchem')"))
    print("1 flagged:", js(view, "spellMisspelled(first, true).map(w => w.text).join(', ')"))
    js(view, """(() => {
        const w = spellMisspelled(first, true).find(w => w.text === 'flubbergast');
        openSpellMenu(first, w, 10, 10);
        const item = [...spellMenu.children].find(c => c.textContent === 'Tilføj til ordbog');
        item.dispatchEvent(new MouseEvent('mousedown', { bubbles: true, cancelable: true }));
        return true;
    })()""")
    wait = QEventLoop()
    QTimer.singleShot(500, wait.quit)
    wait.exec()
    print("2 saved in settings:", gui._settings.value("spell_words"))
    print("2 flagged after adding:", js(view, "spellMisspelled(first, true).map(w => w.text).join(', ') || '-'"))

    view2, bridge2 = open_page()
    print("3 new tab flagged:", js(view2, "spellMisspelled(first, true).map(w => w.text).join(', ') || '-'"))
    for b in (bridge, bridge2):
        b.pool.terminate()
    print("DONE")


if __name__ == "__main__":
    main()
