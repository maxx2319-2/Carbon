from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QIcon

from test_text_tools import tools
from test_interpreter_shortcuts import calls, press, window
from test_stress_window import gui, isolated_settings


def colours(btn):
    image = btn.icon().pixmap(btn.iconSize(), QIcon.Disabled if not btn.isEnabled() else QIcon.Normal).toImage()
    return {QColor(image.pixel(x, y)).name() for x in range(image.width()) for y in range(image.height()) if image.pixelColor(x, y).alpha() == 255}


def marker(w):
    return next(b for b in w.text_tools.findChildren(gui.QToolButton) if b.toolTip() == "Fremhævning")


def test_marker_is_grey_on_math_line(window):
    press(window, Qt.Key_1)
    assert colours(marker(window)) == {gui.SIDEBAR}


def test_marker_is_white_on_text_line(window):
    press(window, Qt.Key_2)
    assert colours(marker(window)) == {gui.BUTTON}


def test_undo_is_grey_when_disabled(window):
    assert not window.undo_btn.isEnabled()
    assert colours(window.undo_btn) == {gui.SIDEBAR}
