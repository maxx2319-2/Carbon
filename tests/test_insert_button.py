import json

from test_interpreter_shortcuts import calls, settle, window
from test_stress_window import gui, isolated_settings, js


def insert_menu(w):
    btn = next(b for b in w.findChildren(gui.QToolButton) if b.text() == "Indsæt")
    return btn, {a.text(): a for a in btn.menu().actions()}


def test_insert_button_has_section(window):
    btn, actions = insert_menu(window)
    assert list(actions) == ["Sektion"]
    assert btn.isEnabled()


def test_section_inserts_header_and_line(window):
    _, actions = insert_menu(window)
    before = json.loads(js(window.interpreter_view, "JSON.stringify(lines().map(modeOf))"))
    actions["Sektion"].trigger()
    settle(400)
    after = json.loads(js(window.interpreter_view, "JSON.stringify(lines().map(modeOf))"))
    assert after == before + ["section", "math"]
    assert js(window.interpreter_view, "modeOf(lastField)") == "section"
