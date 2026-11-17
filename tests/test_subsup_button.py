from test_interpreter_shortcuts import calls, settle, window
from test_stress_window import gui, isolated_settings, js


def subsup(w):
    return next(b for b in w.findChildren(gui.RichButton) if b.source == "SubSup.svg")


def position(btn):
    grid = btn.parentWidget().layout()
    return grid.getItemPosition(grid.indexOf(btn))[:2]


def test_button_sits_after_f_of_x(window):
    btn = subsup(window)
    fx = next(b for b in btn.parentWidget().findChildren(gui.QPushButton) if b.text() == "f(x)=")
    row, col = position(fx)
    assert position(btn) == (row, col + 1)


def test_icon_files_exist():
    assert (gui.ASSETS_DIR / "SubSup.svg").exists()
    assert (gui.ASSETS_DIR / "SubSup_Hover.svg").exists()


def test_click_inserts_sub_and_superscript(window):
    view = window.interpreter_view
    js(view, "setSheet([['code', '']]); focusLine(lines()[0]); true")
    settle(200)
    subsup(window).click()
    settle(400)
    for step in ('["insert", "x"]', '"moveToNextPlaceholder"', '["insert", "2"]', '"moveToNextPlaceholder"', '["insert", "1"]'):
        js(view, f"lines()[0].executeCommand({step}); true")
        settle(100)
    assert js(view, "strip(lines()[0].value)") == "x_2^1"
