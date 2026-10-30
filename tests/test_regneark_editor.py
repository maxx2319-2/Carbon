import json
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6.QtWebEngineWidgets")
from PySide6.QtCore import QEventLoop, QPoint, Qt, QTimer, QUrl
from PySide6.QtTest import QTest
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QApplication

from path import resource_path

app = QApplication.instance() or QApplication([])
CMD = Qt.ControlModifier
LONG = "1+" * 150 + "1"


def pump(ms=200):
    loop = QEventLoop()
    QTimer.singleShot(ms, loop.quit)
    loop.exec()


@pytest.fixture(scope="module")
def view():
    v = QWebEngineView()
    v.resize(600, 400)
    v.show()
    loop = QEventLoop()
    v.loadFinished.connect(loop.quit)
    v.load(QUrl.fromLocalFile(str(resource_path("Assets_math_live/regneark.html"))))
    QTimer.singleShot(10000, loop.quit)
    loop.exec()
    pump(500)
    yield v
    v.close()


def js(view, code):
    out = []
    loop = QEventLoop()
    view.page().runJavaScript(code, 0, lambda r: (out.append(r), loop.quit()))
    QTimer.singleShot(5000, loop.quit)
    loop.exec()
    assert out, "timed out"
    return out[0]


def sheet(view, *lines, line=0, offset=0):
    js(view, f"editor.scrollLeft = 0; setSheet({json.dumps([['code', c] for c in lines])}); focusLine(lines()[{line}]); lines()[{line}].position = {offset}; true")
    pump()


def code(view):
    return json.loads(js(view, "JSON.stringify(lines().map(l => strip(l.value)))"))


def press(view, key, mods=Qt.NoModifier, times=1):
    for _ in range(times):
        QTest.keyClick(view.focusProxy(), key, mods)
        pump(100)
    pump()


def test_scrolling_moves_every_line(view):
    sheet(view, LONG, "2")
    left = "JSON.stringify(lines().map(l => l.getBoundingClientRect().left))"
    before = json.loads(js(view, left))
    js(view, "editor.scrollLeft = 200; true")
    pump()
    after = json.loads(js(view, left))
    assert [b - a for a, b in zip(after, before)] == [200, 200]
    assert js(view, "lines()[0].shadowRoot.querySelector('[part=content]').scrollLeft") == 0


def test_line_numbers_stay_while_scrolling(view):
    sheet(view, LONG, "2")
    js(view, "editor.scrollLeft = 200; true")
    pump()
    assert js(view, "getComputedStyle(lines()[1], '::before').transform") == "matrix(1, 0, 0, 1, 200, 0)"


def test_line_numbers_use_the_app_background(view):
    js(view, "setBackground('#123456'); true")
    assert js(view, "getComputedStyle(lines()[0], '::before').backgroundColor") == "rgb(18, 52, 86)"
    js(view, "setBackground('#404040'); true")


def test_editor_follows_the_caret(view):
    sheet(view, LONG)
    visible = """(() => { const c = lines()[0].shadowRoot.querySelector('.ML__caret').getBoundingClientRect();
        const b = editor.getBoundingClientRect(); return c.left >= b.left + 48 && c.right <= b.left + editor.clientWidth; })()"""
    js(view, "lines()[0].position = lines()[0].lastOffset; true")
    pump()
    assert js(view, "editor.scrollLeft") > 0
    assert js(view, visible)
    QTest.keyClicks(view.focusProxy(), "+2+2+2")
    pump()
    assert js(view, visible)
    js(view, "lines()[0].position = 0; true")
    pump()
    assert js(view, "editor.scrollLeft") == 0


def test_enter_at_end_of_long_line_scrolls_back(view):
    sheet(view, LONG)
    js(view, "lines()[0].position = lines()[0].lastOffset; true")
    pump()
    assert js(view, "editor.scrollLeft") > 0
    press(view, Qt.Key_Return)
    assert js(view, "lines().length") == 2
    assert js(view, "editor.scrollLeft") == 0


def test_arrow_down_to_short_line_scrolls_back(view):
    sheet(view, LONG, "2")
    js(view, "lines()[0].position = lines()[0].lastOffset; true")
    pump()
    press(view, Qt.Key_Down)
    assert js(view, "document.activeElement === lines()[1]")
    assert js(view, "editor.scrollLeft") == 0


def test_click_while_scrolled_does_not_jump(view):
    sheet(view, LONG, LONG, line=1)
    js(view, "editor.scrollLeft = 1000; true")
    pump()
    top, bottom = json.loads(js(view, "JSON.stringify((r => [r.top, r.bottom])(lines()[0].getBoundingClientRect()))"))
    QTest.mouseClick(view.focusProxy(), Qt.LeftButton, Qt.NoModifier, QPoint(300, int((top + bottom) / 2)))
    pump()
    assert js(view, "document.activeElement === lines()[0]")
    assert js(view, "editor.scrollLeft") == 1000


def test_arrow_up_into_long_line_follows_caret(view):
    sheet(view, LONG, "2", line=1)
    press(view, Qt.Key_Up)
    assert js(view, "document.activeElement === lines()[0]")
    assert js(view, "editor.scrollLeft") > 0


def test_shift_down_selects_into_next_line(view):
    sheet(view, "abc", "def", "ghi", line=0, offset=1)
    press(view, Qt.Key_Down, Qt.ShiftModifier)
    assert js(view, "selectedText()") == "bc\nd"


def test_unfocused_part_of_selection_is_highlighted(view):
    sheet(view, "abc", "def", line=0, offset=1)
    press(view, Qt.Key_Down, Qt.ShiftModifier)
    assert js(view, "document.activeElement === lines()[1]")
    assert js(view, "lines()[0].classList.contains('multi')")
    background = js(view, "(el => el ? getComputedStyle(el).backgroundColor : 'missing')(lines()[0].shadowRoot.querySelector('.ML__selection'))")
    assert background not in ("missing", "rgba(0, 0, 0, 0)", "transparent")


def test_shift_left_at_line_start_goes_to_previous_line(view):
    sheet(view, "abc", "def", line=1, offset=0)
    press(view, Qt.Key_Left, Qt.ShiftModifier, times=2)
    assert js(view, "selectedText()") == "c\n"


def test_select_all_and_copy(view):
    sheet(view, "a", "b", "c", line=1)
    press(view, Qt.Key_A, CMD)
    press(view, Qt.Key_C, CMD)
    assert app.clipboard().text() == "a\nb\nc"


def test_typing_replaces_selection_across_lines(view):
    sheet(view, "abc", "def", "ghi", line=0, offset=1)
    press(view, Qt.Key_Down, Qt.ShiftModifier, times=2)
    QTest.keyClicks(view.focusProxy(), "x")
    pump()
    assert code(view) == ["axhi"]


def test_backspace_deletes_selection_and_undo_brings_it_back(view):
    sheet(view, "abc", "def", "ghi", line=0, offset=1)
    press(view, Qt.Key_Down, Qt.ShiftModifier)
    press(view, Qt.Key_Backspace)
    assert code(view) == ["aef", "ghi"]
    press(view, Qt.Key_Z, CMD)
    assert code(view) == ["abc", "def", "ghi"]


def test_enter_over_selection_splits_the_line(view):
    sheet(view, "abc", "def", line=0, offset=1)
    press(view, Qt.Key_Down, Qt.ShiftModifier)
    press(view, Qt.Key_Return)
    assert code(view) == ["a", "ef"]


def test_cut(view):
    sheet(view, "abc", "def", "ghi", line=0, offset=1)
    press(view, Qt.Key_Down, Qt.ShiftModifier)
    press(view, Qt.Key_X, CMD)
    assert app.clipboard().text() == "bc\nd"
    assert code(view) == ["aef", "ghi"]


def test_paste_several_lines(view):
    sheet(view, "ab", line=0, offset=1)
    app.clipboard().setText("1+1\n2+2\n3+3")
    press(view, Qt.Key_V, CMD)
    assert code(view) == ["a1+1", "2+2", "3+3b"]


def test_drag_across_lines(view):
    sheet(view, "abc", "def", "ghi")
    rects = json.loads(js(view, "JSON.stringify(lines().map(l => { const r = l.getBoundingClientRect(); return [r.left, (r.top + r.bottom) / 2]; }))"))
    at = lambda i, dx: QPoint(int(rects[i][0] + dx), int(rects[i][1]))
    proxy = view.focusProxy()
    QTest.mousePress(proxy, Qt.LeftButton, Qt.NoModifier, at(0, 20))
    pump(100)
    QTest.mouseMove(proxy, at(1, 30))
    pump(100)
    QTest.mouseMove(proxy, at(2, 300))
    pump(100)
    QTest.mouseRelease(proxy, Qt.LeftButton, Qt.NoModifier, at(2, 300))
    pump()
    assert js(view, "selectedText()").split("\n")[1:] == ["def", "ghi"]
    assert js(view, "document.activeElement === lines()[2]")
