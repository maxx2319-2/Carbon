import json

import pytest

pytest.importorskip("PySide6")
from PySide6.QtCore import QEventLoop, QTimer, QUrl
from PySide6.QtWebEngineCore import QWebEnginePage
from PySide6.QtWidgets import QApplication

from path import resource_path


PNG = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="


def wait(start):
    loop = QEventLoop()
    out = []
    start(lambda result: (out.append(result), loop.quit()))
    QTimer.singleShot(10000, loop.quit)
    loop.exec()
    assert out, "timed out"
    return out[0]


@pytest.fixture(scope="module")
def page():
    app = QApplication.instance() or QApplication([])
    page = QWebEnginePage()
    url = QUrl.fromLocalFile(str(resource_path("Assets_math_live/regneark.html")))
    assert wait(lambda done: (page.loadFinished.connect(done), page.load(url)))
    yield page
    del page, app


def js(page, code):
    return wait(lambda done: page.runJavaScript(code, done))


def set_sheet(page, rows):
    js(page, f"setSheet({json.dumps(rows)}); true")


def get_sheet(page):
    return json.loads(js(page, "JSON.stringify(getSheet())"))


def test_round_trip_keeps_code_and_outputs(page):
    rows = [
        ["code", r"x=\frac{1}{2}"],
        ["result", r"\Rightarrow\:\mathrm{0.5}"],
        ["code", r"y=x+2"],
        ["error", r"\Rightarrow\:\text{Error: nope}"],
        ["code", r"z=3"],
        ["image", PNG],
    ]
    set_sheet(page, rows)
    assert get_sheet(page) == rows


def test_empty_sheet_gives_one_empty_line(page):
    set_sheet(page, [["code", "x=1"], ["code", "y=2"]])
    set_sheet(page, [])
    assert get_sheet(page) == [["code", ""]]


def test_plot_comes_back_interactive(page):
    data = {"functions": [{"js": "Math.pow(x, 2)", "label": "x^{2}"}], "start": -1, "end": 1}
    set_sheet(page, [["code", "f"], ["plot", json.dumps(data)]])
    assert js(page, "editor.querySelector('div.plot canvas') !== null")
    rows = get_sheet(page)
    assert rows[0] == ["code", "f"]
    assert rows[1][0] == "plot"
    assert json.loads(rows[1][1]) == data


def test_evil_plot_is_not_run(page):
    data = {"functions": [{"js": "(window.pwned = true, x)", "label": "x"}], "start": -1, "end": 1}
    set_sheet(page, [["code", "f"], ["plot", json.dumps(data)]])
    assert js(page, "typeof window.pwned") == "undefined"
    assert js(page, "editor.querySelector('div.plot') === null")
    assert get_sheet(page)[1] == ["error", r"\Rightarrow\:\text{Grafen kunne ikke indlæses}"]


def test_loop_follows_its_line_when_outputs_are_cleared(page):
    set_sheet(page, [
        ["code", "a=1"],
        ["result", r"\Rightarrow\:\mathrm{1}"],
        ["code", "a=a+1"],
        ["code", r"Loop\left(3,3,2\right)"],
    ])
    js(page, "clearOutput(lines()[0]); true")
    assert get_sheet(page)[-1] == ["code", r"Loop\left(2,2,2\right)"]


def test_open_clears_undo_history(page):
    set_sheet(page, [["code", "x=1"]])
    assert js(page, "undoStack.length") == 0
