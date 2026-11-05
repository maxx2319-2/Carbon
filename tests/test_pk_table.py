import pytest
from PySide6.QtWidgets import QLabel, QLineEdit, QListWidget, QPushButton

from test_stress_window import chem, gui, isolated_settings, settle, window


@pytest.fixture
def pka():
    saved = dict(chem.pKa_values)
    yield chem.pKa_values
    chem.pKa_values.clear()
    chem.pKa_values.update(saved)


@pytest.fixture
def table(window, pka):
    window.open_settings()
    settle(400)
    box = window.settings_page.findChildren(QListWidget)[0].parentWidget()
    name, value = box.findChildren(QLineEdit)[:2]
    buttons = {b.text(): b for b in box.findChildren(QPushButton) if b.text() in ("+", "Nulstil")}

    def add(n, v):
        name.setText(n)
        value.setText(v)
        buttons["+"].click()

    return add, buttons["Nulstil"]


def shown(window):
    lst = window.settings_page.findChildren(QListWidget)[0]
    return [lst.itemWidget(lst.item(i)).findChild(QLabel).text() for i in range(lst.count())]


def expected(pka):
    return [f"{k}: {v}" for k, v in sorted(pka.items(), key=lambda kv: kv[0].lower())]


def delete(window, name):
    lst = window.settings_page.findChildren(QListWidget)[0]
    for i in range(lst.count()):
        row = lst.itemWidget(lst.item(i))
        if row.findChild(QLabel).text().startswith(f"{name}: "):
            row.findChild(QPushButton).click()
            return


def test_find_pk_ignores_case():
    assert chem.find_pk({"testsyre": 4.0}, "TestSyre") == 4.0
    assert chem.find_pk({"testsyre": 4.0}, "andensyre") is None


def test_pH_accepts_any_case(pka):
    pka["testsyre"] = 4.0
    assert chem.pH("TESTSYRE", 0.1) == chem.pH("testsyre", 0.1)


def test_adding_another_case_replaces_the_entry(table, pka):
    add, _ = table
    add("Saltsyre", "-6")
    assert [k for k in pka if k.lower() == "saltsyre"] == ["Saltsyre"]
    assert pka["Saltsyre"] == -6


@pytest.mark.parametrize("value", ["inf", "-inf", "nan", "1e999"])
def test_non_finite_values_are_rejected(table, pka, value):
    add, _ = table
    add("nysyre", value)
    assert "nysyre" not in pka


def test_reset_asks_and_restores_defaults(table, pka, window, isolated_settings):
    add, reset = table
    add("nysyre", "4")
    assert isolated_settings.value("pKa_values")
    asked = []
    window.ask_close = lambda title, text, accept="Luk": asked.append(accept) or True
    reset.click()
    assert asked == ["Nulstil"]
    assert dict(pka) == gui.PK_DEFAULTS["pKa_values"]
    assert isolated_settings.value("pKa_values") is None


def test_list_stays_sorted_and_matches_the_data(table, pka, window):
    add, reset = table
    add("Aaa", "1")
    add("zzz", "2")
    add("Mmm", "3")
    delete(window, "saltsyre")
    add("aaa", "4")
    add("Mmm", "5")
    delete(window, "zzz")
    assert shown(window) == expected(pka)
    window.ask_close = lambda title, text, accept="Luk": True
    reset.click()
    assert shown(window) == expected(pka)


def test_reset_can_be_cancelled(table, pka, window):
    add, reset = table
    add("nysyre", "4")
    window.ask_close = lambda title, text, accept="Luk": False
    reset.click()
    assert pka["nysyre"] == 4
