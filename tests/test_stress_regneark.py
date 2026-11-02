import json
import os
import subprocess
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6.QtWebEngineWidgets")
from PySide6.QtCore import QEventLoop, QTimer, QUrl
from PySide6.QtTest import QTest
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QApplication

from path import resource_path

app = QApplication.instance() or QApplication([])
SRC = Path(__file__).resolve().parent.parent / "src"


def pump(ms=200):
    loop = QEventLoop()
    QTimer.singleShot(ms, loop.quit)
    loop.exec()


def open_view():
    v = QWebEngineView()
    v.resize(900, 700)
    v.show()
    loop = QEventLoop()
    v.loadFinished.connect(loop.quit)
    v.load(QUrl.fromLocalFile(str(resource_path("Assets_math_live/regneark.html"))))
    QTimer.singleShot(15000, loop.quit)
    loop.exec()
    pump(800)
    return v


def js(view, code, timeout=30000):
    out = []
    loop = QEventLoop()
    view.page().runJavaScript(code, 0, lambda r: (out.append(r), loop.quit()))
    QTimer.singleShot(timeout, loop.quit)
    loop.exec()
    if not out:
        raise TimeoutError(code[:80])
    return out[0]


@pytest.fixture
def view():
    v = open_view()
    yield v
    v.close()
    v.deleteLater()
    pump(300)


TYPE = """(() => {{ {setup} const mf = lines()[0]; mf.focus(); mf.position = mf.lastOffset; const t = performance.now();
    for (let i = 0; i < {keys}; i++) {{ mf.executeCommand(["typedText", "1"]); mf.dispatchEvent(new Event("input")); }}
    return JSON.stringify({{ms: (performance.now() - t) / {keys}, entries: undoStack.length, bytes: JSON.stringify(undoStack).length}}); }})()"""


def test_200_line_file_opens_quickly(view):
    ms = js(view, """(() => { const rows = []; for (let i = 0; i < 200; i++) rows.push(["code", "x_{" + i + "}=" + i + "\\\\cdot2"]);
        const t = performance.now(); setSheet(rows); editor.offsetHeight; return performance.now() - t; })()""", 120000)
    assert ms < 3000


def test_300_result_rows_render(view):
    ms = js(view, """(() => { setSheet([["code", "1"]]); const rows = [["code", "1"]];
        for (let i = 0; i < 300; i++) rows.push(["result", "\\\\Rightarrow\\\\:\\\\mathrm{" + i + ".0}"]);
        const t = performance.now(); showOutput(rows, lines()); editor.offsetHeight; return performance.now() - t; })()""", 120000)
    assert ms < 5000
    assert js(view, "editor.querySelectorAll('math-field.out').length") == 300


@pytest.mark.xfail(reason="R-09: very long results sit near MathLive's recursion limit and sometimes throw RangeError, which stops showOutput", strict=False)
def test_210000_character_result_renders(view):
    result = js(view, """(() => { try { setSheet([["code","1"],["code","2"]]);
        showOutput([["code","1"],["result","\\\\mathrm{" + "Met,\\\\ ".repeat(30000) + "}"],["code","2"],["result","\\\\mathrm{2.0}"]], lines());
        return "shown " + editor.querySelectorAll(".out").length; } catch (e) { return "threw " + e.name; } })()""", 120000)
    assert result == "shown 2"


def test_plot_with_300_functions_draws(view):
    result = js(view, """(() => { setSheet([["code",""]]); const fns = []; for (let i = 0; i < 300; i++) fns.push({js: "x+" + i, label: "x+" + i});
        try { showOutput([["code",""],["plot", JSON.stringify({functions: fns, start: -10, end: 10})]], lines()); return "ok"; }
        catch (e) { return e.name; } })()""", 120000)
    assert result == "ok"


@pytest.mark.xfail(reason="P-03: setSheet builds every math-field one by one, 1000 lines take about 10 s", strict=True)
def test_1000_line_file_opens_in_reasonable_time(view):
    ms = js(view, """(() => { const rows = []; for (let i = 0; i < 1000; i++) rows.push(["code", "x_{" + i + "}=" + i + "\\\\cdot2"]);
        const t = performance.now(); setSheet(rows); editor.offsetHeight; return performance.now() - t; })()""", 120000)
    assert ms < 3000


@pytest.mark.xfail(reason="P-03: each result row is a new math-field and the cost grows with the square of the count", strict=True)
def test_1000_result_rows_render_quickly(view):
    ms = js(view, """(() => { setSheet([["code", "1"]]); const rows = [["code", "1"]];
        for (let i = 0; i < 1000; i++) rows.push(["result", "\\\\Rightarrow\\\\:\\\\mathrm{" + i + ".0}"]);
        const t = performance.now(); showOutput(rows, lines()); editor.offsetHeight; return performance.now() - t; })()""", 120000)
    assert ms < 3000


@pytest.mark.xfail(reason="P-03: every keystroke re-renders and recolours the whole line", strict=True)
def test_typing_on_a_1000_term_line_stays_responsive(view):
    result = json.loads(js(view, TYPE.format(setup='setSheet([["code", "1+".repeat(1000) + "1"]]);', keys=5), 120000))
    assert result["ms"] < 100


@pytest.mark.xfail(reason="P-04: every keystroke pushes a full copy of the sheet onto undoStack with no limit", strict=True)
def test_undo_history_is_bounded(view):
    setup = 'const rows = []; for (let i = 0; i < 500; i++) rows.push(["code", "a_{" + i + "}=" + "1+".repeat(20) + "1"]); setSheet(rows);'
    result = json.loads(js(view, TYPE.format(setup=setup, keys=300), 300000))
    assert result["entries"] <= 200 or result["bytes"] < 2_000_000


@pytest.mark.xfail(reason="R-01: result rows are ordinary editable math-fields, so typing changes them and they get saved", strict=True)
def test_result_rows_cannot_be_edited(view):
    js(view, r"""setSheet([["code","1+1"],["result","\\Rightarrow\\:\\mathrm{2.0}"]]); true""")
    pump(500)
    before = js(view, "editor.querySelector('math-field.out').value")
    js(view, "const o = editor.querySelector('math-field.out'); o.focus(); o.position = o.lastOffset; true")
    pump(300)
    QTest.keyClicks(view.focusProxy(), "999")
    pump(500)
    assert js(view, "editor.querySelector('math-field.out').value") == before


@pytest.mark.xfail(reason="B-15: multi-line paste puts plain text straight into the LaTeX value, so % starts a comment", strict=True)
def test_multi_line_paste_keeps_percent_signs(view):
    values = json.loads(js(view, r"""(() => {
        setSheet([["code",""]]); const mf = lines()[0]; mf.focus();
        const dt = new DataTransfer(); dt.setData("text/plain", "50% af 20\n2+2");
        mf.dispatchEvent(new ClipboardEvent("paste", {clipboardData: dt, bubbles: true, cancelable: true}));
        return JSON.stringify(lines().map(l => l.getValue("ascii-math")));
    })()"""))
    assert "%" in values[0]


@pytest.mark.xfail(reason="B-16: the LOOP regex has no room for spaces, so Loop(2, 2, 3) is not renumbered when results are added", strict=True)
def test_loop_with_spaces_follows_its_lines(view):
    js(view, r"""(() => { setSheet([["code","x=0"],["code","x+=1"],["code","Loop\\left(2,\\:2,\\:3\\right)"]]);
        showOutput([["code",""],["result","0"],["code",""],["result","1"],["code",""],["result","2"]], lines()); return true; })()""")
    pump(300)
    assert js(view, "strip(lines()[2].value)").replace(r"\:", "") == r"Loop\left(3,3,3\right)"


@pytest.mark.xfail(reason="C-02: one bad plot row throws inside setSheet and stops the rest of the file from loading", strict=True)
def test_corrupt_plot_row_does_not_stop_loading(view):
    result = js(view, r"""(() => { try { setSheet([["code","1+1"],["plot","{bad json"],["code","2+2"]]); return JSON.stringify(lines().map(l => strip(l.value))); } catch (e) { return "threw " + e.name; } })()""")
    assert result == '["1+1","2+2"]'


@pytest.mark.xfail(reason="C-02: a file whose rows aren't a list wipes the open sheet before failing", strict=True)
def test_malformed_file_leaves_the_sheet_alone(view):
    result = js(view, r"""(() => { setSheet([["code","keep me"],["code","and me"]]); try { setSheet({rows: 1}); } catch (e) {} return JSON.stringify(lines().map(l => strip(l.value))); })()""")
    assert result == '["keep me","and me"]'


@pytest.mark.xfail(reason="R-02: Math.min(...ys) spreads every sample as an argument and overflows the call stack", strict=True)
def test_plot_with_1000_functions_draws(view):
    result = js(view, """(() => { setSheet([["code",""]]); const fns = []; for (let i = 0; i < 1000; i++) fns.push({js: "x+" + i, label: "x+" + i});
        try { showOutput([["code",""],["plot", JSON.stringify({functions: fns, start: -10, end: 10})]], lines()); return "ok"; }
        catch (e) { return e.name; } })()""", 300000)
    assert result == "ok"


@pytest.mark.xfail(reason="S-02: image rows from a file are used as img.src without checking them", strict=True)
def test_remote_image_rows_are_refused(view):
    src = js(view, r"""(() => { setSheet([["code","1"],["image","https://example.invalid/pixel.png"]]); const img = editor.querySelector("img"); return img ? img.src : ""; })()""")
    assert not src.startswith("http")


@pytest.mark.xfail(reason="WIP-01: addSection is declared inside plotElement, so Python can't call it", strict=True)
def test_add_section_can_be_called(view):
    assert js(view, "typeof addSection") == "function"


ZOOM = r"""
import os, sys
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = "--disable-gpu --log-level=3"
from PySide6.QtCore import QEventLoop, QTimer, QUrl
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QApplication
from path import resource_path
app = QApplication([])
def js(v, code, timeout=8000):
    out = []
    loop = QEventLoop()
    v.page().runJavaScript(code, 0, lambda r: (out.append(r), loop.quit()))
    QTimer.singleShot(timeout, loop.quit)
    loop.exec()
    return bool(out)
v = QWebEngineView()
v.resize(900, 700)
v.show()
loop = QEventLoop()
v.loadFinished.connect(loop.quit)
v.load(QUrl.fromLocalFile(str(resource_path("Assets_math_live/regneark.html"))))
loop.exec()
js(v, 'setSheet([["code",""]]); showOutput([["code",""],["plot", JSON.stringify({functions: [{js: "x*x", label: "x^2"}], start: -10, end: 10})]], lines()); true')
for _ in range(40):
    alive = js(v, "(() => { const c = editor.querySelector('div.plot canvas'); const r = c.getBoundingClientRect(); for (let i = 0; i < 10; i++) c.dispatchEvent(new WheelEvent('wheel', {deltaY: -100, ctrlKey: true, clientX: r.left + r.width * 0.75, clientY: r.top + r.height * 0.3, bubbles: true, cancelable: true})); return true; })()")
    if not alive:
        print("FROZE", flush=True)
        os._exit(0)
print("OK", flush=True)
os._exit(0)
"""


@pytest.mark.xfail(reason="C-01: zooming far into a plot makes the grid loop in draw() run forever and the page freezes", strict=True)
def test_deep_plot_zoom_does_not_freeze():
    env = {**os.environ, "QT_QPA_PLATFORM": "offscreen"}
    try:
        proc = subprocess.run([sys.executable, "-c", ZOOM], cwd=SRC, env=env, capture_output=True, text=True, timeout=180)
    except subprocess.TimeoutExpired:
        pytest.fail("zoom test did not finish")
    assert proc.stdout.strip().splitlines()[-1] == "OK"
