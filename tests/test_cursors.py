import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6.QtWebEngineWidgets")
from PySide6.QtWidgets import QApplication, QPushButton, QComboBox
from PySide6.QtCore import Qt

app = QApplication.instance() or QApplication([])
import gui


@pytest.fixture(scope="module")
def window():
    w = gui.MainWindow()
    w.show()
    app.processEvents()
    yield w
    w.close()


def shape(widget):
    return widget.cursor().shape()


def test_panel_buttons_point():
    panel = gui.DraggablePanel("pH", gui.PANELS["pH"].build())
    panel.show()
    app.processEvents()
    assert shape(panel.header) == Qt.ArrowCursor
    header_buttons = panel.header.findChildren(QPushButton)
    assert header_buttons and all(shape(b) == Qt.PointingHandCursor for b in header_buttons)
    beregn = next(b for b in panel.body.findChildren(QPushButton) if b.text() == "Beregn")
    assert shape(beregn) == Qt.PointingHandCursor


def test_window_buttons_keep_arrow(window):
    for btn in (window.back_btn, window.forward_btn, window.max_btn):
        assert shape(btn) == Qt.ArrowCursor


def test_drawer_buttons_point_without_own_setcursor(window):
    window.drawer.ensurePolished()
    buttons = window.drawer.findChildren(QPushButton)
    assert buttons and all(shape(b) == Qt.PointingHandCursor for b in buttons)


def test_settings_controls_point(window):
    window.settings_page.ensurePolished()
    combo = window.settings_page.findChild(QComboBox)
    assert shape(combo) == Qt.PointingHandCursor
    toggles = [b for b in window.settings_page.findChildren(QPushButton) if b.isCheckable()]
    assert toggles and all(shape(b) == Qt.PointingHandCursor for b in toggles)


def test_mathfield_uses_text_cursor():
    html = (gui.resource_path("Assets_math_live") / "mathfield.html").read_text(encoding="utf-8")
    assert "cursor: text;" in html
