import pytest
from PySide6.QtCore import Qt

from test_interpreter_shortcuts import calls, insert, press, window
from test_stress_window import isolated_settings


def tools(w):
    return w.text_tools.isEnabled(), w.bold_btn.isChecked(), w.italic_btn.isChecked()


def test_tools_disabled_on_math_line(window):
    press(window, Qt.Key_1)
    assert tools(window) == (False, False, False)


def test_tools_enabled_on_text_line(window):
    press(window, Qt.Key_2)
    assert tools(window) == (True, False, False)


def test_bold_unlit_after_switching_to_math(window):
    press(window, Qt.Key_2)
    press(window, Qt.Key_B)
    assert tools(window) == (True, True, False)
    press(window, Qt.Key_1)
    assert tools(window) == (False, False, False)


def test_ctrl_b_on_math_line_does_not_light_bold(window):
    press(window, Qt.Key_1)
    insert(window, "x")
    press(window, Qt.Key_B)
    assert tools(window) == (False, False, False)
