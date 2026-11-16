import json
import subprocess
import sys
from pathlib import Path

import pytest

pytest.importorskip("PySide6.QtWebEngineWidgets")
import gui

SRC = Path(__file__).resolve().parent.parent / "src"


def evaluate(*lines):
    return json.loads(gui._InterpreterBridge.evaluate(None, json.dumps(list(lines))))


def defs(*lines):
    return json.loads(next(data for kind, data, *_ in evaluate(*lines) if kind == "defs"))


def test_variables():
    assert defs("a=5", r"b=3\:\mathrm{m}", "v_{0}=12", r"\alpha=0.5") == [
        r"a=\mathrm{5.0}", r"b=\mathrm{3.0\ m}", r"v_{0}=\mathrm{12.0}", r"α=\mathrm{0.5}",
    ]


def test_vector():
    assert defs(r"\overrightarrow{v}=\left\lbrace1,2,3\right\rbrace") == [
        r"\overrightarrow{v}=\begin{pmatrix}\mathrm{1}\\\mathrm{2}\\\mathrm{3}\end{pmatrix}",
    ]


def test_string():
    assert defs(r"s=\text{'hej'}") == [r's=\text{"hej"}']


def test_functions():
    assert defs("f(x)=x^2+2x", r"g(x,y)=\frac{x}{y}") == [
        r"f\left(x\right)=x^{2} + 2 x", r"g\left(x,y\right)=\frac{x}{y}",
    ]


def test_redefinition_shows_latest_value():
    assert defs("a=5", "a=a+1") == [r"a=\mathrm{6.0}"]


def test_nothing_defined():
    assert defs("2+2") == []


def test_defs_row_never_reaches_the_sheet():
    bridge = gui._InterpreterBridge.__new__(gui._InterpreterBridge)
    gui.QObject.__init__(bridge)
    got, sheet = [], []
    bridge.definitionsChanged.connect(got.append)
    bridge.finished.connect(lambda run_id, rows: sheet.append(json.loads(rows)))
    bridge.done(1, gui._InterpreterBridge.evaluate(None, json.dumps(["a=5"])), False)
    assert json.loads(got[0]) == [r"a=\mathrm{5.0}"]
    assert all(row[0] != "defs" for row in sheet[0])


SCRIPT = r"""
import json, os, sys, tempfile, time
os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, sys.argv[1])
import gui
os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = "--disable-gpu --disable-gpu-compositing --log-level=3"
from PySide6.QtCore import QEventLoop, QSettings, QTimer
from PySide6.QtWidgets import QApplication

app = QApplication([])
s = QSettings(os.path.join(tempfile.mkdtemp(), "c.ini"), QSettings.IniFormat)
s.setValue("changelog_seen", gui.version)
gui._settings = s

def pump(ms):
    loop = QEventLoop(); QTimer.singleShot(ms, loop.quit); loop.exec()

def wait_for(cond, timeout=20000):
    end = time.perf_counter() + timeout / 1000
    while time.perf_counter() < end:
        if cond():
            return True
        pump(50)
    return cond()

def js(view, code):
    out = []; loop = QEventLoop(); view.page().runJavaScript(code, 0, lambda r: (out.append(r), loop.quit())); QTimer.singleShot(10000, loop.quit); loop.exec(); return out[0] if out else None

w = gui.MainWindow(); w.resize(1400, 900); w.show()
w.open_interpreter()
first = w.interpreter_view
wait_for(lambda: js(first, "typeof getSheet") == "function")
dl = w.definition_list
dropdown = dl.parentWidget().parentWidget()
out = {"loaded_while_closed": wait_for(lambda: dl.loaded, 10000)}

rows = [["code", "a=5"], ["code", r"\overrightarrow{v}=\left\lbrace1,2,3\right\rbrace"], ["code", "f(x)=x^2+2x"]]
js(first, f"setSheet({json.dumps(rows)}); run(); true")
wait_for(lambda: getattr(first, "definitions", "[]") != "[]")
out["defs"] = json.loads(getattr(first, "definitions", "[]"))
pump(500)

dropdown.header.setChecked(True)
wait_for(lambda: dl.height() > 60, 5000)
pump(800)
out["open"] = dl.height()
img = dl.grab().toImage()
out["coloured"] = sum(img.pixelColor(x, y).name() != gui.BG.lower() for x in range(img.width()) for y in range(img.height()))

w.new_interpreter_tab()
wait_for(lambda: js(w.interpreter_view, "typeof getSheet") == "function")
wait_for(lambda: dl.height() < 40, 5000)
out["new_tab"] = dl.height()

w.interpreter_tabs.setCurrentIndex(0)
wait_for(lambda: dl.height() > 60, 5000)
out["back"] = dl.height()
print(json.dumps(out), flush=True)
for bridge in w.findChildren(gui._InterpreterBridge):
    bridge.pool.terminate()
os._exit(0)
"""


@pytest.fixture(scope="module")
def gui_run():
    out = subprocess.run([sys.executable, "-c", SCRIPT, str(SRC)], capture_output=True, text=True, encoding="utf-8", timeout=180)
    return json.loads(next(l for l in out.stdout.splitlines() if l.startswith("{")))


def test_sidebar_gets_definitions(gui_run):
    assert len(gui_run["defs"]) == 3


def test_page_loads_while_dropdown_is_closed(gui_run):
    assert gui_run["loaded_while_closed"]


def test_opened_dropdown_fits_and_renders(gui_run):
    assert gui_run["open"] > 60
    assert gui_run["coloured"] > 200


def test_new_tab_shows_empty_list(gui_run):
    assert gui_run["new_tab"] < 40


def test_switching_back_restores_list(gui_run):
    assert gui_run["back"] == gui_run["open"]
