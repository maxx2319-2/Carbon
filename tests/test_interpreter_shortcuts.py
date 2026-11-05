import json

import pytest
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest

from test_stress_window import gui, isolated_settings, js, ready, settle, wait_for


@pytest.fixture
def calls(monkeypatch):
    called = []
    monkeypatch.setattr(gui.MainWindow, "open_regneark", lambda self: called.append("open"))
    monkeypatch.setattr(gui.MainWindow, "save_regneark_as", lambda self: called.append("save_as"))
    return called


@pytest.fixture
def window(calls):
    w = gui.MainWindow()
    w.resize(1400, 900)
    w.show()
    ready(w.interpreter_view)
    w.open_interpreter()
    settle(400)
    yield w
    w.ask_close = lambda title, text: True
    w.close()
    w.deleteLater()
    settle(300)


def lines(w):
    return json.loads(js(w.interpreter_view, "JSON.stringify(lines().map(l => strip(l.value)))"))


def insert(w, text):
    js(w.interpreter_view, f"lines()[0].executeCommand(['insert', '{text}']); true")
    settle(200)


def press(w, key, modifiers=Qt.ControlModifier):
    w.focus_interpreter()
    settle(200)
    QTest.keyClick(w.interpreter_view.focusProxy(), key, modifiers)
    settle(400)


def buttons(w):
    return w.undo_btn.isEnabled(), w.redo_btn.isEnabled()


def test_buttons_start_disabled(window):
    assert buttons(window) == (False, False)


def test_undo_and_redo_buttons(window):
    insert(window, "1")
    insert(window, "2")
    assert lines(window) == ["12"]
    assert buttons(window) == (True, False)
    window.undo_btn.click()
    settle(300)
    assert lines(window) == ["1"]
    assert buttons(window) == (True, True)
    window.redo_btn.click()
    settle(300)
    assert lines(window) == ["12"]
    assert buttons(window) == (True, False)


def test_new_edit_clears_redo(window):
    insert(window, "1")
    insert(window, "2")
    window.undo_btn.click()
    settle(300)
    insert(window, "3")
    assert lines(window) == ["13"]
    assert buttons(window) == (True, False)


@pytest.mark.parametrize("key, modifiers", [
    (Qt.Key_Y, Qt.ControlModifier),
    (Qt.Key_Z, Qt.ControlModifier | Qt.ShiftModifier),
])
def test_redo_keys(window, key, modifiers):
    insert(window, "1")
    insert(window, "2")
    press(window, Qt.Key_Z)
    assert lines(window) == ["1"]
    press(window, key, modifiers)
    assert lines(window) == ["12"]


def test_buttons_follow_the_current_tab(window):
    insert(window, "1")
    insert(window, "2")
    window.new_interpreter_tab()
    assert ready(window.interpreter_view)
    assert wait_for(lambda: buttons(window) == (False, False), 3000)
    window.interpreter_tabs.setCurrentIndex(0)
    assert wait_for(lambda: buttons(window) == (True, False), 3000)


def test_ctrl_t_opens_a_tab(window):
    press(window, Qt.Key_T)
    assert window.interpreter_tabs.count() == 2
    assert window.interpreter_tabs.currentIndex() == 1


def test_ctrl_w_closes_the_tab(window):
    window.new_interpreter_tab()
    assert ready(window.interpreter_view)
    press(window, Qt.Key_W)
    assert window.interpreter_tabs.count() == 1


def test_ctrl_tab_switches_and_wraps(window):
    window.new_interpreter_tab()
    assert ready(window.interpreter_view)
    assert window.interpreter_tabs.currentIndex() == 1
    press(window, Qt.Key_Tab)
    assert window.interpreter_tabs.currentIndex() == 0
    press(window, Qt.Key_Backtab, Qt.ControlModifier | Qt.ShiftModifier)
    assert window.interpreter_tabs.currentIndex() == 1


def test_ctrl_o_opens(window, calls):
    press(window, Qt.Key_O)
    assert calls == ["open"]


def test_ctrl_shift_s_saves_as(window, calls):
    press(window, Qt.Key_S, Qt.ControlModifier | Qt.ShiftModifier)
    assert calls == ["save_as"]
