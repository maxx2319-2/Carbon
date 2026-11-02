import json

import pytest
from PySide6.QtCore import QPoint, Qt
from PySide6.QtTest import QTest

from test_regneark_editor import CMD, js, press, pump, view


def load(view, *rows, line=0):
    js(view, f"setSheet({json.dumps([['code', *r] for r in rows])}); focusLine(lines()[{line}]); true")
    pump()


def modes(view):
    return json.loads(js(view, "JSON.stringify(lines().map(modeOf))"))


def sent(view):
    js(view, "bridge = {run: (id, text) => window.sent = JSON.parse(text)}; run(); bridge = null; true")
    return json.loads(js(view, "JSON.stringify(sent)"))


def test_only_math_lines_are_run(view):
    load(view, ["1+1"], [r"\text{hej}", "text"], ["x^2", "formula"])
    assert sent(view) == ["1+1", "", ""]


def test_modes_survive_save_and_load(view):
    rows = [["code", "1+1"], ["code", r"\text{hej}", "text"], ["code", "x^2", "formula"]]
    js(view, f"setSheet({json.dumps(rows)}); true")
    assert json.loads(js(view, "JSON.stringify(getSheet())")) == rows


def test_old_files_open_as_math(view):
    js(view, "setSheet([['code', '1+1']]); true")
    assert modes(view) == ["math"]
    assert json.loads(js(view, "JSON.stringify(getSheet())")) == [["code", "1+1"]]


def test_shortcuts_switch_mode(view):
    load(view, ["1+1"])
    press(view, Qt.Key_2, CMD)
    assert modes(view) == ["text"]
    press(view, Qt.Key_3, CMD)
    assert modes(view) == ["formula"]
    press(view, Qt.Key_1, CMD)
    assert modes(view) == ["math"]


def test_typing_in_text_mode_keeps_spaces(view):
    load(view, [""])
    press(view, Qt.Key_2, CMD)
    QTest.keyClicks(view.focusProxy(), "hej med dig")
    pump()
    assert "hej med dig" in js(view, "strip(lines()[0].value)")


def test_text_line_types_text_at_the_start(view):
    load(view, [r"\text{dig}", "text"])
    js(view, "lines()[0].position = 0; true")
    QTest.keyClicks(view.focusProxy(), "hej ")
    pump()
    assert js(view, "strip(lines()[0].value)") == r"\text{hej dig}"


def test_math_keys_are_plain_in_text_lines(view):
    load(view, [r"\text{a}", "text"])
    js(view, "lines()[0].position = lines()[0].lastOffset; true")
    QTest.keyClicks(view.focusProxy(), "/[_")
    pump()
    assert js(view, "strip(lines()[0].value)") == r"\text{a/\lbrack\_}"


def test_text_lines_get_no_colours(view):
    load(view, ["Afstem 12"], [r"\text{Afstem 12}", "text"])
    assert r"\textcolor" in js(view, "lines()[0].value")
    assert r"\textcolor" not in js(view, "lines()[1].value")


def test_enter_keeps_the_mode(view):
    load(view, [r"\text{hej}", "text"])
    js(view, "lines()[0].position = lines()[0].lastOffset; true")
    press(view, Qt.Key_Return)
    assert modes(view) == ["text", "text"]


def test_undo_restores_mode(view):
    load(view, ["1+1"])
    press(view, Qt.Key_2, CMD)
    press(view, Qt.Key_Z, CMD)
    assert modes(view) == ["math"]


def test_mode_applies_to_whole_selection(view):
    load(view, ["a"], ["b"], ["c"])
    press(view, Qt.Key_Down, Qt.ShiftModifier)
    press(view, Qt.Key_3, CMD)
    assert modes(view) == ["formula", "formula", "math"]


def test_formula_line_number_uses_accent(view):
    load(view, ["x^2", "formula"], ["1+1"])
    colour = "getComputedStyle(lines()[{}], '::before').color"
    assert js(view, colour.format(0)) == "rgb(111, 198, 251)"
    assert js(view, colour.format(1)) == "rgb(133, 133, 133)"


def test_line_type_slider(view):
    import gui
    window = gui.MainWindow()
    pump(2500)
    slider = window.line_type
    assert [b.text() for b in slider.buttons.values()] == ["Matematik", "Tekst", "Formel"]
    slider.buttons["text"].click()
    pump()
    assert json.loads(js(window.interpreter_view, "JSON.stringify(lines().map(modeOf))")) == ["text"]
    js(window.interpreter_view, "setMode('formula'); true")
    pump()
    assert slider.current == "formula"
    window.close_confirmed = True
    window.close()


def test_typing_after_switch_uses_the_new_type(view):
    load(view, [r"\text{abc}", "text"])
    press(view, Qt.Key_1, CMD)
    QTest.keyClicks(view.focusProxy(), "xy")
    pump()
    assert json.loads(js(view, "JSON.stringify(lines().map(l => strip(l.value)))")) == [r"\text{abc}xy"]


def test_slider_ignores_arrow_keys_but_follows_clicks(view):
    import gui
    window = gui.MainWindow()
    window.show()
    window.activateWindow()
    window.open_interpreter()
    pump(2500)
    page = window.interpreter_view
    js(page, r"setSheet([['code', '1+1'], ['code', '\\text{hej}', 'text']]); true")
    pump()
    QTest.keyClick(page.focusProxy(), Qt.Key_Down)
    pump()
    assert window.line_type.current == "math"
    top, bottom = json.loads(js(page, "JSON.stringify((r => [r.top, r.bottom])(lines()[1].getBoundingClientRect()))"))
    QTest.mouseClick(page.focusProxy(), Qt.LeftButton, Qt.NoModifier, QPoint(100, int((top + bottom) / 2)))
    pump()
    assert window.line_type.current == "text"
    window.close_confirmed = True
    window.close()
