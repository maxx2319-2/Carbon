import pytest
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest

from test_regneark_editor import CMD, js, press, pump, view
from test_regneark_modes import load


@pytest.fixture
def text_line(view):
    for _ in range(100):
        if js(view, "spell.ready"):
            break
        pump(100)
    load(view, [""])
    press(view, Qt.Key_2, CMD)
    return view


def words(view):
    return js(view, "spellWords(lines()[0]).map(w => w.text).join(' ')")


def flagged(view):
    return js(view, "spellMisspelled(lines()[0], true).map(w => w.text).join(' ')")


@pytest.mark.parametrize("typed", ["teh ", "konstnaten ", "bestemmmelse.", "untill, ", "Vi skal beregne teh ende "])
def test_typing_never_changes_a_misspelled_word(text_line, typed):
    QTest.keyClicks(text_line.focusProxy(), typed)
    pump()
    assert words(text_line) == " ".join(typed.replace(".", " ").replace(",", " ").split())
    assert flagged(text_line) == {"Vi skal beregne teh ende ": "teh"}.get(typed, typed.strip(" .,"))


def test_picking_a_suggestion_still_replaces_the_word(text_line):
    QTest.keyClicks(text_line.focusProxy(), "teh ")
    pump()
    picked = js(text_line, """(() => {
        openSpellMenu(lines()[0], spellMisspelled(lines()[0], true)[0], 10, 10);
        const item = spellMenu.querySelector('.fix');
        item.dispatchEvent(new MouseEvent('mousedown', { bubbles: true, cancelable: true }));
        return item.textContent;
    })()""")
    pump()
    assert picked
    assert words(text_line) == picked
    assert flagged(text_line) == ""
