from PySide6.QtTest import QTest

from gui import Latex_to_calc
from test_regneark_editor import code, js, pump, sheet, view


def test_brace_closes_itself(view):
    sheet(view, "")
    QTest.keyClicks(view.focusProxy(), "{2")
    pump()
    assert code(view) == [r"\left\lbrace2\right\rbrace"]


def test_typed_after_brace_goes_inside(view):
    sheet(view, "")
    QTest.keyClicks(view.focusProxy(), "1+{2")
    pump()
    assert Latex_to_calc(code(view)[0]) == Latex_to_calc(r"1+\lbrace2\rbrace")


def test_mathfield_brace_closes_itself():
    from PySide6.QtCore import QEventLoop, QTimer, QUrl
    from PySide6.QtWebEngineWidgets import QWebEngineView
    from path import resource_path
    v = QWebEngineView()
    v.resize(400, 40)
    v.show()
    loop = QEventLoop()
    v.loadFinished.connect(loop.quit)
    v.load(QUrl.fromLocalFile(str(resource_path("Assets_math_live/mathfield.html"))))
    QTimer.singleShot(10000, loop.quit)
    loop.exec()
    pump(500)
    v.setFocus()
    js(v, "mf.focus(); true")
    pump()
    QTest.keyClicks(v.focusProxy(), "{2")
    pump()
    assert js(v, "mf.value") == r"\left\lbrace2\right\rbrace"
    v.close()


def test_brace_is_plain_in_text_lines(view):
    js(view, "setSheet([['code', '\\\\text{a}', 'text']]); focusLine(lines()[0]); lines()[0].position = lines()[0].lastOffset; true")
    pump()
    QTest.keyClicks(view.focusProxy(), "{")
    pump()
    assert r"\left" not in code(view)[0]
