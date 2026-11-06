import pytest
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest

from test_regneark_editor import CMD, js, press, pump, view

STYLES = {"bold": ("{fontSeries: 'b'}", "textbf"), "italic": ("{fontShape: 'it'}", "textit")}


def setup_text(view):
    js(view, "setSheet([['code', '']]); focusLine(lines()[0]); true")
    pump()
    press(view, Qt.Key_2, CMD)
    js(view, "(lastField ?? first)._mathfield.defaultStyle = {}; (lastField ?? first)._mathfield.styleBias = 'left'; true")


def toggle(view, s):
    js(view, f"format({STYLES[s][0]}, 'toggle'); true")
    pump()


def query(view, s):
    return js(view, f"(lastField ?? first).queryStyle({STYLES[s][0]})")


def type_(view, text):
    QTest.keyClicks(view.focusProxy(), text)
    pump()


@pytest.mark.parametrize("s", ["bold", "italic"])
def test_toggle_on_off_on_while_typing(view, s):
    setup_text(view)
    states = []
    toggle(view, s); states.append(query(view, s))
    type_(view, "hej"); states.append(query(view, s))
    toggle(view, s); states.append(query(view, s))
    type_(view, "x"); states.append(query(view, s))
    toggle(view, s); states.append(query(view, s))
    type_(view, "y"); states.append(query(view, s))
    cmd = STYLES[s][1]
    assert states == ["all", "all", "none", "none", "all", "all"]
    assert js(view, "(lastField ?? first).value") == rf"\text{{\{cmd}{{hej}}x\{cmd}{{y}}}}"
