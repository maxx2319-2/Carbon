import json
import os
import random
import stat
import subprocess
import sys
import threading
import time
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6.QtWebEngineWidgets")
from PySide6.QtCore import QEventLoop, QPoint, QSettings, Qt, QTimer
from PySide6.QtNetwork import QNetworkReply
from PySide6.QtTest import QTest
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QApplication, QLineEdit, QListWidget, QMessageBox, QPushButton, QToolButton, QWidget

app = QApplication.instance() or QApplication([])
import chem
import gui
import license_manager

SRC = Path(__file__).resolve().parent.parent / "src"
PORTAL = b"<!DOCTYPE html>\n<html><body>Log ind paa skolens net</body></html>"


def pump(ms=200):
    loop = QEventLoop()
    QTimer.singleShot(ms, loop.quit)
    loop.exec()


def settle(ms=400):
    caught = []
    end = time.perf_counter() + ms / 1000
    while time.perf_counter() < end:
        try:
            pump(30)
        except Exception as e:
            caught.append(e)
    return caught


def wait_for(cond, timeout=20000):
    end = time.perf_counter() + timeout / 1000
    while time.perf_counter() < end:
        if cond():
            return True
        pump(50)
    return cond()


def js(view, code, timeout=20000):
    out = []
    loop = QEventLoop()
    view.page().runJavaScript(code, 0, lambda r: (out.append(r), loop.quit()))
    QTimer.singleShot(timeout, loop.quit)
    loop.exec()
    if not out:
        raise TimeoutError(code[:80])
    return out[0]


def ready(view):
    return wait_for(lambda: js(view, "typeof getSheet", 5000) == "function")


@pytest.fixture(autouse=True)
def isolated_settings(tmp_path, monkeypatch):
    s = QSettings(str(tmp_path / "carbon.ini"), QSettings.IniFormat)
    s.setValue("changelog_seen", gui.version)
    monkeypatch.setattr(gui, "_settings", s)
    return s


@pytest.fixture
def slot_errors(monkeypatch):
    errors = []
    monkeypatch.setattr(sys, "excepthook", lambda kind, value, tb: errors.append(value))
    monkeypatch.setattr(threading, "excepthook", lambda args: errors.append(args.exc_value))
    return errors


@pytest.fixture
def window():
    w = gui.MainWindow()
    w.resize(1400, 900)
    w.show()
    ready(w.interpreter_view)
    yield w
    w.close_confirmed = True
    w.close()
    w.deleteLater()
    settle(300)


def open_panel(w, key, page="kemi_page"):
    p = getattr(w, page)
    if w.stack.currentWidget() is not p:
        w.slide_to(p)
        settle(450)
    p.show_panel(key)
    body = p.panels[key].body
    views = body.findChildren(QWebEngineView)
    wait_for(lambda: all(getattr(v, "_loaded", True) for v in views))
    fields = sorted(body.findChildren(gui.MathInput), key=lambda f: f.mapTo(body, QPoint(0, 0)).y())
    outputs = sorted(body.findChildren(gui.MathOutput) + body.findChildren(gui.TextOutput), key=lambda f: f.mapTo(body, QPoint(0, 0)).y())
    button = [b for b in body.findChildren(QPushButton) if b.text() == "Beregn"][0]
    return body, fields, outputs, button


def calc(w, key, *texts, page="kemi_page"):
    body, fields, outputs, button = open_panel(w, key, page)
    for f, t in zip(fields, texts):
        f.setText(t)
    button.click()
    settle(300)
    return body, fields, outputs


def field_box(view):
    return json.loads(js(view, """(() => { const c = mf.shadowRoot.querySelector('.ML__latex') || mf.shadowRoot.querySelector('.ML__content');
        const r = c.getBoundingClientRect(), m = mf.getBoundingClientRect();
        return JSON.stringify({font: parseFloat(getComputedStyle(mf).fontSize), width: r.width, room: mf.clientWidth, bottom: r.bottom, field_bottom: m.bottom}); })()"""))


class FakeReply:
    def __init__(self, body=b"", error=QNetworkReply.NoError):
        self.body, self.err = body, error

    def error(self):
        return self.err

    def readAll(self):
        return self.body

    def deleteLater(self):
        pass


EDGE_INPUTS = {
    "unit": [("5[km]", "m"), ("1,5[m]", "cm"), ("", "m"), ("abc", "")],
    "pH": [("4.76", "0.1"), ("4,76", "0,1"), ("4.76", "0"), ("abc", "-1")],
    "pOH": [("4.75", "0.1"), ("ammoniak", "0.1")],
    "balance": [("H2O->H2+O2", ""), ("H2O", ""), ("", "syre")],
    "analysis": [("C6H12O6",), ("co2",), ("Xx",)],
    "bjerrum": [("4.76",), ("abc",), ("",)],
    "udbytteprocent": [("4.5[g]", "5[g]"), ("3[kg]", "0[kg]")],
    "volumenprocent": [("40[ml]", "100[ml]"), ("", "1")],
    "masseprocent": [("12[g]", "50[g]"), ("x", "y")],
    "mængdeberegning": [("10[g]", "", "", "", "58.44[g/mol]", ""), ("abc", "", "", "", "1", "")],
    "puffer": [("0.1", "0.1", "4.76"), ("0", "0.1", "4.76")],
    "h3o": [("7",), ("abc",), ("1e400",)],
    "dna_peptid": [("ATGGCCTAA",), ("xyz",), ("ATG" * 400,)],
    "rna_peptid": [("AUGGCCUAA",), ("ATG",)],
}


def test_every_panel_survives_edge_inputs(window, slot_errors):
    for key, cases in EDGE_INPUTS.items():
        page = "biotek_page" if key in ("dna_peptid", "rna_peptid") else "kemi_page"
        for case in cases:
            calc(window, key, *case, page=page)
        getattr(window, page).panels[key].hide()
    assert slot_errors == []


def test_rapid_navigation_keeps_the_header_in_sync(window, slot_errors):
    pages = [window.stack.widget(i) for i in range(window.stack.count())]
    rng = random.Random(3)
    for _ in range(400):
        window.slide_to(rng.choice(pages))
        pump(rng.choice([0, 1, 5, 30]))
    settle(800)
    current = window.stack.currentIndex()
    button = window.page_buttons.button(current)
    assert window.page_buttons.checkedId() == (current if button else -1) or button is None
    assert window.page_title.text() == (button.toolTip() if button else window.stack.widget(current).windowTitle())
    assert slot_errors == []


def test_drawer_survives_rapid_toggling(window, slot_errors):
    for i in range(301):
        window.toggle_drawer()
        if i % 3 == 0:
            pump(1)
    settle(800)
    assert window.drawer_open is True
    assert window.drawer.isVisible()
    assert window.drawer.y() == window.toolbar.height()
    assert slot_errors == []


def test_window_survives_extreme_sizes(window, slot_errors):
    window.toggle_drawer()
    settle(400)
    for size in [(600, 1), (1, 1), (6000, 4000), (600, 74), (900, 600)]:
        window.resize(*size)
        pump(100)
        assert window.width() >= 600
        assert window.drawer.height() > 0
    assert slot_errors == []


def test_search_handles_huge_and_odd_queries(window, slot_errors):
    for text in ["x" * 100000, "øæå ÆØÅ 🙂 ‮", "(", "[", "\\", "e"]:
        window.search.setText(text)
        pump(20)
    window.run_search()
    settle(500)
    assert slot_errors == []


def test_many_tabs_keep_the_plus_button_reachable(window, slot_errors):
    window.open_interpreter()
    for _ in range(24):
        window.new_interpreter_tab()
    assert all(ready(window.interpreter_stack.widget(i)) for i in range(window.interpreter_stack.count()))
    settle(500)
    plus = [b for b in window.stack.widget(1).findChildren(QToolButton) if b.text() == "+"][0]
    assert window.width() == 1400
    assert 0 < plus.mapTo(window, QPoint(0, 0)).x() < window.width()
    while window.interpreter_tabs.count() > 1:
        window.remove_interpreter_tab(window.interpreter_stack.widget(1), False)
    settle(500)
    assert window.interpreter_tabs.count() == 1
    assert slot_errors == []


def test_long_tab_name_does_not_widen_the_window(window):
    window.open_interpreter()
    window.set_tab_name(window.interpreter_view, "A" * 2000)
    settle(300)
    assert window.width() == 1400
    assert window.minimumSizeHint().width() < 800


def test_panel_drag_is_clamped_to_the_page(window):
    window.open_kemi()
    settle(400)
    panel = window.kemi_page.panels.get("unit") or (window.kemi_page.show_panel("unit") or window.kemi_page.panels["unit"])
    QTest.mousePress(panel.header, Qt.LeftButton, Qt.NoModifier, QPoint(10, 10))
    for step in range(0, 5000, 250):
        QTest.mouseMove(panel.header, QPoint(10 + step, 10 + step))
    QTest.mouseRelease(panel.header, Qt.LeftButton, Qt.NoModifier, QPoint(10, 10))
    settle(200)
    assert window.kemi_page.canvas.rect().contains(panel.geometry())


def test_closed_tabs_release_their_processes(window):
    psutil = pytest.importorskip("psutil")

    def processes():
        return {p.pid for p in psutil.Process().children(recursive=True) if p.name().lower().startswith(("qtwebengine", "python"))}

    before = processes()
    views = [window.new_interpreter_tab() for _ in range(6)]
    assert all(ready(v) for v in views)
    for v in views:
        js(v, "setSheet([['code','1+1']]); run(); true")
    settle(3000)
    started = processes() - before
    assert started
    for v in views:
        window.remove_interpreter_tab(v, False)
    assert wait_for(lambda: not (processes() & started), 15000)


@pytest.mark.xfail(reason="P-06: every MathInput/MathOutput is its own QWebEngineView with its own renderer process (55 processes, 1.6 GB with all panels open)", strict=True)
def test_panel_fields_share_renderer_processes(window):
    body_unit, *_ = open_panel(window, "unit")
    body_ph, *_ = open_panel(window, "pH")
    views = body_unit.findChildren(QWebEngineView) + body_ph.findChildren(QWebEngineView)
    assert len({v.page().renderProcessPid() for v in views}) <= 2


def test_failed_save_is_reported(window, tmp_path):
    locked = tmp_path / "locked.crbn"
    locked.write_text('{"rows": []}', encoding="utf-8")
    os.chmod(locked, stat.S_IREAD)
    seen = []

    def watch():
        m = QApplication.activeModalWidget()
        if isinstance(m, QMessageBox):
            seen.append(m.text())
            m.close()

    watcher = QTimer()
    watcher.timeout.connect(watch)
    watcher.start(50)
    try:
        window.interpreter_view.setProperty("path", str(locked))
        js(window.interpreter_view, "setSheet([['code','1+1']]); true")
        window.save_regneark()
        settle(1500)
    finally:
        watcher.stop()
        os.chmod(locked, stat.S_IWRITE | stat.S_IREAD)
    assert seen


def test_closing_a_tab_during_a_calculation_is_quiet(window, slot_errors):
    view = window.new_interpreter_tab()
    ready(view)
    js(view, r"setSheet([['code','x=0'],['code','x+1'],['code','\\mathrm{Loop}\\left(2,2,100000\\right)']]); run(); true")
    settle(500)
    workers = list(view.findChild(gui._InterpreterBridge).pool._pool)
    window.remove_interpreter_tab(view, False)
    settle(1500)
    assert slot_errors == []
    assert workers and not any(p.is_alive() for p in workers)


@pytest.mark.parametrize("handler, body", [("draw_smiles", b""), ("draw_smiles", PORTAL), ("show_name", PORTAL)])
def test_molecule_lookup_reports_odd_replies(window, handler, body):
    window.molecule_status.clear()
    getattr(window, handler)(FakeReply(body))
    assert window.molecule_status.text()


@pytest.mark.xfail(reason="M-07: a lookup without internet says 'Ikke fundet' instead of saying there is no connection", strict=True)
def test_offline_lookup_says_there_is_no_connection(window):
    window.draw_smiles(FakeReply(b"", QNetworkReply.HostNotFoundError))
    assert "forbindelse" in window.molecule_status.text().lower()


def test_changelog_handles_an_unreadable_reply(window):
    window.show_changelog(FakeReply(b"\xe6\xf8\xe5 nyheder"))


@pytest.mark.xfail(reason="M-08: Esc doesn't close the changelog overlay, which grabs the keyboard", strict=True)
def test_escape_closes_the_changelog(window):
    window.show_changelog(FakeReply("# Bv 2.0\n- Nyt".encode()))
    settle(200)
    QTest.keyClick(window.changelog, Qt.Key_Escape)
    settle(200)
    visible = window.changelog.isVisible()
    window.close_changelog()
    assert not visible


@pytest.mark.xfail(reason="B-26: the help text says 'samlet' goes in the first box, but the panel's first box is 'Specifik'", strict=True)
@pytest.mark.parametrize("key, build", [("volumenprocent", gui.volumen_panel), ("masseprocent", gui.masse_panel)])
def test_percent_help_lists_inputs_in_panel_order(key, build):
    body = build()
    first, second = [f._placeholder.lower() for f in body.findChildren(gui.MathInput)][:2]
    body.deleteLater()
    help_text = gui.HELPTEXT[key].lower()
    assert help_text.find(first.split("[")[0]) < help_text.find(second.split("[")[0])


def test_double_click_on_tab_close_does_not_add_a_tab(window):
    view = window.new_interpreter_tab()
    ready(view)
    index = window.interpreter_stack.indexOf(view)
    window.close_interpreter_tab(index)
    window.close_interpreter_tab(index)
    settle(1500)
    assert window.interpreter_tabs.count() == 1


@pytest.mark.xfail(reason="B-28: '4,76' (Danish decimal comma) silently becomes two curves, pKs 4 and pKs 76", strict=True)
def test_bjerrum_decimal_comma_is_one_value(window):
    body, *_ = calc(window, "bjerrum", "4,76")
    canvases = [c for c in body.findChildren(QWidget) if type(c).__name__ == "FigureCanvasQTAgg"]
    labels = [l.get_label() for l in canvases[-1].figure.axes[0].get_lines() if l.get_label().startswith("pKs")]
    assert len(labels) <= 1


@pytest.mark.xfail(reason="B-29: the same .crbn can be opened in two tabs, and each save overwrites the other", strict=True)
def test_opening_an_open_file_reuses_its_tab(window, tmp_path):
    path = tmp_path / "ark.crbn"
    path.write_text(json.dumps({"rows": [["code", "1"]]}), encoding="utf-8")
    window.load_regneark(str(path))
    window.load_regneark(str(path))
    settle(1500)
    paths = [window.interpreter_stack.widget(i).property("path") for i in range(window.interpreter_stack.count())]
    assert paths.count(str(path)) == 1


@pytest.mark.xfail(reason="B-30: acid names are looked up case-sensitively", strict=True)
def test_acid_names_ignore_case(window, monkeypatch):
    monkeypatch.setitem(chem.pKa_values, "testsyre", 4.0)
    body, fields, outputs = calc(window, "pH", "Testsyre", "0.1")
    assert not outputs[0].text().startswith("Error")


@pytest.mark.xfail(reason="U-01: the close prompts check 'not empty' instead of the unsaved dot, so saved sheets still ask", strict=True)
def test_saved_sheets_close_without_asking(window):
    asked = []
    window.ask_close = lambda title, text: asked.append(title) or False
    view = window.new_interpreter_tab()
    ready(view)
    js(view, "setSheet([['code','1+1']]); true")
    settle(300)
    assert not view.property("dirty")
    window.close_interpreter_tab(window.interpreter_stack.indexOf(view))
    settle(800)
    window.close()
    settle(1200)
    assert asked == []


@pytest.mark.xfail(reason="U-02: 'Luk' is the default button, so Enter in 'Vil du lukke?' throws the work away", strict=True)
def test_enter_in_the_close_dialog_cancels(window):
    ticks = []

    def tick():
        m = QApplication.activeModalWidget()
        if not isinstance(m, QMessageBox):
            return
        ticks.append(1)
        if len(ticks) == 4:
            QTest.keyClick(QApplication.focusWidget() or m, Qt.Key_Return)
        if len(ticks) == 30:
            m.reject()

    timer = QTimer()
    timer.timeout.connect(tick)
    timer.start(50)
    try:
        result = window.ask_close("Luk side", "Vil du lukke Ny Fil?")
    finally:
        timer.stop()
    assert result is False


@pytest.mark.xfail(reason="U-04: activation runs on the GUI thread, so the license dialog freezes until the server answers", strict=True)
def test_license_activation_keeps_the_dialog_responsive(monkeypatch):
    monkeypatch.setattr(license_manager, "check_license", lambda key: (True, {"expires": "2099-01-01"}))
    monkeypatch.setattr(license_manager, "activate", lambda key: (time.sleep(0.6), (False, "Ingen forbindelse"))[1])
    dialog = gui.LicenseWindow()
    dialog.show()
    ticks = []
    timer = QTimer()
    timer.timeout.connect(lambda: ticks.append(1))
    timer.start(50)
    [b for b in dialog.findChildren(QPushButton) if b.text() == "Ok"][0].click()
    timer.stop()
    dialog.deleteLater()
    assert ticks


@pytest.mark.xfail(reason="U-04: an invalid key is replaced by the error text, so the student has to retype it", strict=True)
def test_license_error_keeps_the_typed_key(monkeypatch):
    monkeypatch.setattr(license_manager, "check_license", lambda key: (False, "Ugyldig licens"))
    dialog = gui.LicenseWindow()
    dialog.key_input.setText("MIN-NØGLE-123")
    [b for b in dialog.findChildren(QPushButton) if b.text() == "Ok"][0].click()
    text = dialog.key_input.text()
    dialog.deleteLater()
    assert text == "MIN-NØGLE-123"


@pytest.mark.xfail(reason="U-06: Esc doesn't cancel renaming a tab", strict=True)
def test_escape_cancels_a_tab_rename(window):
    window.open_interpreter()
    settle(400)
    window.rename_tab(0)
    pill = window.interpreter_tabs.tabButton(0, gui.QTabBar.LeftSide).findChild(QLineEdit)
    QTest.keyClicks(pill, "abc")
    QTest.keyClick(pill, Qt.Key_Escape)
    settle(200)
    assert window.tab_name(0) == "Ny Fil"


@pytest.mark.xfail(reason="R-10: long results shrink to 7 px and are cut off in the 27 px output box", strict=True)
def test_long_panel_result_stays_readable(window):
    body, fields, outputs = calc(window, "dna_peptid", "ATG" * 60, page="biotek_page")
    settle(600)
    box = field_box(outputs[0])
    assert box["font"] >= 10 and box["width"] <= box["room"]


@pytest.mark.xfail(reason="R-11: unit fractions like mol/ml are drawn as \\frac and the denominator is cut off", strict=True)
def test_unit_fraction_result_is_not_clipped(window):
    body, fields, outputs = calc(window, "unit", "2.5[mol/l]", "mol/ml")
    settle(600)
    box = field_box(outputs[0])
    assert box["bottom"] <= box["field_bottom"] - 1


@pytest.mark.xfail(reason="R-12: regneark.html asks for the font 'Segoe-UI', which doesn't exist", strict=True)
def test_autocomplete_uses_the_ui_font(window):
    family = js(window.interpreter_view, "getComputedStyle(document.getElementById('suggest')).fontFamily")
    assert "Segoe UI" in family


@pytest.mark.xfail(reason="R-13: panel inputs have no '->' shortcut, so arrows show as '− >'", strict=True)
def test_panel_inputs_turn_arrows_into_arrows(window):
    body, fields, outputs, button = open_panel(window, "balance")
    assert js(fields[0], "String(mf.inlineShortcuts['->'])") != "undefined"


@pytest.mark.xfail(reason="R-14: panel errors go through calc_to_latex, so they render in math mode as 'Error :'", strict=True)
def test_panel_errors_render_as_text(window):
    body, fields, outputs = calc(window, "unit", "5[m]", "")
    settle(400)
    assert "\\text" in js(outputs[0], "mf.value")


@pytest.mark.xfail(reason="R-15: the Fil button isn't auto-raised, so Save_Hover.svg is never shown", strict=True)
def test_save_button_shows_its_hover_icon(window):
    window.open_interpreter()
    settle(600)
    button = [b for b in window.stack.widget(1).findChildren(QToolButton) if b.toolTip() == "Fil"][0]
    button.setAttribute(Qt.WA_UnderMouse, False)
    normal = button.grab().toImage()
    button.setAttribute(Qt.WA_UnderMouse, True)
    hover = button.grab().toImage()
    assert normal != hover


@pytest.mark.xfail(reason="E-04: a Danish decimal comma gives the function syntax as the error instead of a hint", strict=True)
def test_decimal_comma_gets_a_danish_hint(window):
    body, fields, outputs = calc(window, "unit", "1,5[m]", "cm")
    assert "punktum" in outputs[0].text().lower()


@pytest.mark.xfail(reason="P-07: Analyse runs on the GUI thread and freezes the window for about a second", strict=True)
def test_analyse_keeps_the_window_responsive(window):
    body, fields, outputs, button = open_panel(window, "analysis")
    fields[0].setText("C6H12O6")
    ticks = []
    timer = QTimer()
    timer.timeout.connect(lambda: ticks.append(1))
    timer.start(50)
    t = time.perf_counter()
    button.click()
    blocked = time.perf_counter() - t
    timer.stop()
    assert ticks or blocked < 0.2


@pytest.mark.xfail(reason="P-08: importing gui takes 2-4 s because chem pulls in parser, mendeleev, pyplot and scipy", strict=True)
def test_gui_imports_in_under_a_second():
    env = {**os.environ, "QT_QPA_PLATFORM": "offscreen", "MPLBACKEND": "agg"}
    code = "import time; t = time.perf_counter(); import gui; print(time.perf_counter() - t)"
    proc = subprocess.run([sys.executable, "-c", code], cwd=SRC, env=env, capture_output=True, text=True, timeout=120)
    assert float(proc.stdout.strip().splitlines()[-1]) < 1.0


@pytest.mark.xfail(reason="P-09: every add/remove in the pK table rebuilds all rows, so the cost grows with the square of the size", strict=True)
def test_pk_table_add_stays_fast_with_200_entries(window):
    saved = dict(chem.pKa_values)
    try:
        chem.pKa_values.update({f"syre{i:03d}": 5.0 for i in range(200)})
        window.open_settings()
        settle(400)
        box = window.settings_page.findChildren(QListWidget)[0].parentWidget()
        name, value = box.findChildren(QLineEdit)[:2]
        name.setText("ny syre")
        value.setText("4")
        t = time.perf_counter()
        [b for b in box.findChildren(QPushButton) if b.text() == "+"][0].click()
        elapsed = time.perf_counter() - t
    finally:
        chem.pKa_values.clear()
        chem.pKa_values.update(saved)
    assert elapsed < 0.15


@pytest.mark.xfail(reason="C-08: a damaged pKs table in the settings stops MainWindow from being created", strict=True)
def test_corrupt_stored_pk_table_does_not_stop_startup(isolated_settings):
    saved = dict(chem.pKa_values)
    isolated_settings.setValue("pKa_values", "{not json")
    try:
        w = gui.MainWindow()
        w.close_confirmed = True
        w.close()
        w.deleteLater()
    finally:
        chem.pKa_values.clear()
        chem.pKa_values.update(saved)


@pytest.mark.xfail(reason="WIP-02: a line in 'section' mode makes SegmentedControl.setCurrent raise KeyError", strict=True)
def test_section_mode_does_not_break_the_mode_switch(window, slot_errors):
    js(window.interpreter_view, "applyMode(lines()[0], 'section'); reportMode(lines()[0]); true")
    settle(500)
    assert slot_errors == []
