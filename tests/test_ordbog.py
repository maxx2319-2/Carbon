import json
from pathlib import Path

from PySide6.QtWidgets import QLabel, QLineEdit, QListWidget, QPushButton

from test_stress_window import gui, isolated_settings, js, ready, settle, wait_for, window


def controls(window):
    box = window.word_table
    entry = box.findChild(QLineEdit)
    buttons = {b.text(): b for b in box.findChildren(QPushButton) if b.text() in ("+", "Nulstil")}

    def add(word):
        entry.setText(word)
        buttons["+"].click()

    return add, buttons["Nulstil"]


def shown(window):
    lst = window.word_table.findChild(QListWidget)
    return [lst.itemWidget(lst.item(i)).findChild(QLabel).text() for i in range(lst.count())]


def delete(window, word):
    lst = window.word_table.findChild(QListWidget)
    for i in range(lst.count()):
        row = lst.itemWidget(lst.item(i))
        if row.findChild(QLabel).text() == word:
            row.findChild(QPushButton).click()
            return


def stored(settings):
    return json.loads(settings.value("spell_words", "[]"))


def accepted(view, word):
    return js(view, f"spell.ignored.has({json.dumps(word)})")


def second_tab(window):
    view = window.new_interpreter_tab()
    ready(view)
    return view


def test_ordbog_sits_under_tilpasning(window):
    assert window.settings_page.findChildren(QListWidget)[0].parentWidget() is window.word_table


def test_words_are_saved_lowercase_and_shown_sorted(window, isolated_settings):
    add, _ = controls(window)
    for word in ("Zebra", "Ferrit", "abe"):
        add(word)
    assert sorted(stored(isolated_settings)) == ["abe", "ferrit", "zebra"]
    assert shown(window) == ["abe", "ferrit", "zebra"]


def test_empty_spaced_and_duplicate_words_are_rejected(window, isolated_settings):
    add, _ = controls(window)
    for word in ("", "   ", "to ord", "ferrit", "FERRIT", " Ferrit "):
        add(word)
    assert stored(isolated_settings) == ["ferrit"]
    assert shown(window) == ["ferrit"]


def test_adding_and_deleting_in_settings_reaches_every_open_tab(window, isolated_settings):
    views = [window.interpreter_view, second_tab(window)]
    add, _ = controls(window)
    add("Xqzvb")
    assert [accepted(v, "xqzvb") for v in views] == [True, True]
    delete(window, "xqzvb")
    assert stored(isolated_settings) == []
    assert shown(window) == []
    assert [accepted(v, "xqzvb") for v in views] == [False, False]


def test_word_added_from_one_tab_reaches_the_other_tabs_and_settings(window, isolated_settings):
    first = window.interpreter_view
    other = second_tab(window)
    js(first, "bridge.addWord('xqzvb'); true")
    settle(300)
    assert stored(isolated_settings) == ["xqzvb"]
    assert accepted(other, "xqzvb")
    window.open_settings()
    settle(400)
    assert shown(window) == ["xqzvb"]


def test_new_tab_loads_the_saved_words(window, isolated_settings):
    add, _ = controls(window)
    add("xqzvb")
    view = second_tab(window)
    assert wait_for(lambda: accepted(view, "xqzvb"), 5000)


def test_reset_asks_clears_and_reaches_every_open_tab(window, isolated_settings):
    views = [window.interpreter_view, second_tab(window)]
    add, reset = controls(window)
    add("xqzvb")
    add("ferrit")
    asked = []
    window.ask_close = lambda title, text, accept="Luk": asked.append(accept) or True
    reset.click()
    assert asked == ["Nulstil"]
    assert isolated_settings.value("spell_words") is None
    assert shown(window) == []
    assert [accepted(v, w) for v in views for w in ("xqzvb", "ferrit")] == [False] * 4


def test_reset_can_be_cancelled(window, isolated_settings):
    add, reset = controls(window)
    add("xqzvb")
    window.ask_close = lambda title, text, accept="Luk": False
    reset.click()
    assert stored(isolated_settings) == ["xqzvb"]
    assert shown(window) == ["xqzvb"]
    assert accepted(window.interpreter_view, "xqzvb")


def test_words_are_on_disk_after_closing_and_load_in_the_next_window(window, isolated_settings):
    add, _ = controls(window)
    add("xqzvb")
    window.close_confirmed = True
    window.close()
    assert "xqzvb" in Path(isolated_settings.fileName()).read_text(encoding="utf-8")
    w = gui.MainWindow()
    try:
        w.show()
        ready(w.interpreter_view)
        assert shown(w) == ["xqzvb"]
        assert wait_for(lambda: accepted(w.interpreter_view, "xqzvb"), 5000)
    finally:
        w.close_confirmed = True
        w.close()
        w.deleteLater()
        settle(300)
