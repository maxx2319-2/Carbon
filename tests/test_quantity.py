import re

import pytest
import requests
import quantity
from quantity import quantity as Q


# --- arithmetic ---

def test_multiply_combines_units():
    assert Q(2, {"m": 1}) * Q(3, {"s": 1}) == Q(6, {"m": 1, "s": 1})


def test_multiply_same_unit_adds_powers():
    assert Q(2, {"m": 1}) * Q(3, {"m": 1}) == Q(6, {"m": 2})


def test_divide_cancels_units():
    assert Q(6, {"m": 1}) / Q(3, {"m": 1}) == Q(2.0, {})


def test_divide_by_unit_gives_negative_power():
    assert Q(1, {}) / Q(2, {"s": 1}) == Q(0.5, {"s": -1})


def test_arithmetic_does_not_change_its_inputs():
    a, b = Q(1, {"m": 1}), Q(1, {"m": 1})
    a * b
    a / b
    a ** 2
    assert a.units == {"m": 1}
    assert b.units == {"m": 1}


@pytest.mark.parametrize("power, expected", [
    (2, Q(4, {"m": 2})),
    (-1, Q(0.5, {"m": -1})),
    (Q(3, {}), Q(8, {"m": 3})),
    (0, Q(1, {})),
])
def test_power(power, expected):
    assert Q(2, {"m": 1}) ** power == expected


def test_square_root_of_area():
    assert Q(4, {"m": 2}) ** 0.5 == Q(2.0, {"m": 1})


def test_power_with_unit_fails():
    with pytest.raises(ValueError, match="unitless"):
        Q(2, {"m": 1}) ** Q(3, {"s": 1})


def test_add():
    assert Q(1, {"m": 1}) + Q(2, {"m": 1}) == Q(3, {"m": 1})


def test_subtract():
    assert Q(5, {"m": 1}) - Q(2, {"m": 1}) == Q(3, {"m": 1})


def test_subtract_to_zero_keeps_unit():
    assert Q(2, {"m": 1}) - Q(2, {"m": 1}) == Q(0, {"m": 1})


@pytest.mark.parametrize("op", [lambda a, b: a + b, lambda a, b: a - b])
def test_add_or_subtract_different_units_fails(op):
    with pytest.raises(ValueError, match="diffrent units"):
        op(Q(1, {"m": 1}), Q(1, {"s": 1}))


# --- display and comparison ---

@pytest.mark.parametrize("q, expected", [
    (Q(2.0, {}), "2.0"),
    (Q(3.0, {"m": 1}), "3.0 m"),
    (Q(1, {"m": 2}), "1 m^2"),
    (Q(0.5, {"m": 1, "s": -1}), "0.5 m/s"),
    (Q(1, {"kg": 1, "m": 2, "s": -2}), "1 kg*m^2/s^2"),
    (Q(1, {"m": 1, "s": -1, "kg": -1}), "1 m/s*kg"),
    (Q(1, {"s": -1}), "1 1/s"),
    (Q(1, {"s": -2}), "1 1/s^2"),
])
def test_str(q, expected):
    assert str(q) == expected


def test_repr():
    assert repr(Q(1.5, {"m": 1})) == "value: 1.5 unit: {'m': 1}"


def test_equal_ignores_unit_order():
    assert Q(1, {"m": 1, "s": 1}) == Q(1, {"s": 1, "m": 1})


def test_different_value_or_unit_is_not_equal():
    assert Q(1, {"m": 1}) != Q(2, {"m": 1})
    assert Q(1, {"m": 1}) != Q(1, {"s": 1})


def test_not_equal_to_plain_number():
    assert Q(1, {}) != 1


# --- unit table ---

def test_bundled_table_has_no_broken_rows():
    rows = quantity._get_df()["unit"].dropna()
    assert len(quantity.retrive_units()) == len(rows)


def test_unit_table_is_cached():
    assert quantity.retrive_units() is quantity.retrive_units()


@pytest.mark.parametrize("name, factor, base", [
    ("m", 1, {"m": 1}),
    ("km", 1e3, {"m": 1}),
    ("cm", 1e-2, {"m": 1}),
    ("mm", 1e-3, {"m": 1}),
    ("µm", 1e-6, {"m": 1}),     # micro sign
    ("μm", 1e-6, {"m": 1}),     # greek mu, looks the same
    ("dam", 10, {"m": 1}),           # two-letter prefix
    ("g", 1e-3, {"kg": 1}),
    ("mg", 1e-6, {"kg": 1}),
    ("kg", 1, {"kg": 1}),
    ("min", 60, {"s": 1}),           # its own unit, not milli-"in"
    ("ms", 1e-3, {"s": 1}),
    ("timer", 3600, {"s": 1}),
    ("dage", 86400, {"s": 1}),
    ("mol", 1, {"mol": 1}),
    ("mmol", 1e-3, {"mol": 1}),
    ("ml", 1e-3, {"l": 1}),
    ("dl", 0.1, {"l": 1}),
    ("m^3", 1000, {"l": 1}),
    ("N", 1, {"m": 1, "kg": 1, "s": -2}),
    ("hPa", 100, {"m": -1, "kg": 1, "s": -2}),
    ("kJ", 1e3, {"m": 2, "kg": 1, "s": -2}),
])
def test_lookup_unit(name, factor, base):
    data = quantity.lookup_unit(name)
    assert data["factor"] == pytest.approx(factor)
    assert data["base_units"] == base


@pytest.mark.parametrize("name", ["foo", "t", "km^3"])
def test_lookup_unknown_unit(name):
    with pytest.raises(ValueError, match=re.escape(f"unknown unit {name}")):
        quantity.lookup_unit(name)


def test_known_unit_names_include_prefixes():
    names = quantity.known_unit_names()
    assert {"m", "km", "mg", "ml", "m^3"} <= set(names)
    assert "km^3" not in names


# --- SI conversion ---

@pytest.mark.parametrize("q, expected", [
    (Q(5, {"km": 1}), Q(5000, {"m": 1})),
    (Q(500, {"g": 1}), Q(0.5, {"kg": 1})),
    (Q(36, {"km": 1, "timer": -1}), Q(10, {"m": 1, "s": -1})),
    (Q(1, {"cm": 2}), Q(1e-4, {"m": 2})),
    (Q(250, {"ml": 1}), Q(0.25, {"l": 1})),
    (Q(2, {"m^3": 1}), Q(2000, {"l": 1})),
    (Q(1, {"N": 1}), Q(1, {"m": 1, "kg": 1, "s": -2})),
    (Q(1, {"J": 1, "s": -1}), Q(1, {"m": 2, "kg": 1, "s": -3})),
    (Q(3, {}), Q(3, {})),
])
def test_si_convert(q, expected):
    result = Q.si_convert(q)
    assert result.value == pytest.approx(expected.value)
    assert result.units == expected.units


def test_si_convert_unknown_unit():
    with pytest.raises(ValueError, match="Ukendt enhed: foo"):
        Q.si_convert(Q(1, {"foo": 1}))


def test_si_convert_unknown_unit_after_known_unit():
    with pytest.raises(ValueError, match="Ukendt enhed: foo"):
        Q.si_convert(Q(1, {"km": 1, "foo": 1}))


# --- reading unit text ---

@pytest.mark.parametrize("text, units", [
    ("m", {"m": 1}),
    ("km/timer", {"km": 1, "timer": -1}),
    ("g/mol", {"g": 1, "mol": -1}),
    ("mol/l", {"mol": 1, "l": -1}),
    ("m^3", {"m^3": 1}),                          # m^3 is its own row in the table
    ("J/mol*K", {"J": 1, "mol": -1, "K": -1}),    # everything after / is in the denominator
    ("xyz", {}),
])
def test_quantity_convert(text, units):
    assert Q.quantity_convert(2, text) == Q(2, units)


@pytest.mark.xfail(reason="a unit that appears twice overwrites the first instead of adding the powers")
@pytest.mark.parametrize("text, units", [
    ("m*m", {"m": 2}),
    ("m/s/s", {"m": 1, "s": -2}),
])
def test_quantity_convert_repeated_unit(text, units):
    assert Q.quantity_convert(1, text).units == units


# --- unit_convert ---

@pytest.mark.parametrize("q, unit, expected", [
    (Q(5, {"km": 1}), "m", Q(5000, {"m": 1})),
    (Q(1500, {"m": 1}), "km", Q(1.5, {"km": 1})),
    (Q(36, {"km": 1, "timer": -1}), "m/s", Q(10, {"m": 1, "s": -1})),
    (Q(10, {"m": 1, "s": -1}), "km/timer", Q(36, {"km": 1, "timer": -1})),
    (Q(90, {"s": 1}), "min", Q(1.5, {"min": 1})),
    (Q(1, {"dage": 1}), "timer", Q(24, {"timer": 1})),
    (Q(1, {"m^3": 1}), "l", Q(1000, {"l": 1})),
    (Q(1, {"l": 1}), "ml", Q(1000, {"ml": 1})),
    (Q(0.018, {"kg": 1, "mol": -1}), "g/mol", Q(18, {"g": 1, "mol": -1})),
    (Q(0.1, {"mol": 1, "l": -1}), "mmol/l", Q(100, {"mmol": 1, "l": -1})),
    (Q(2.5, {"kJ": 1}), "J", Q(2500, {"J": 1})),
])
def test_unit_convert(q, unit, expected):
    result = Q.unit_convert(q, unit)
    assert result.value == pytest.approx(expected.value)
    assert result.units == expected.units


def test_unit_convert_incompatible_units():
    with pytest.raises(ValueError, match="cannot convert"):
        Q.unit_convert(Q(1, {"m": 1}), "s")


def test_unit_convert_unknown_target():
    with pytest.raises(ValueError, match="kan ikke parse unit"):
        Q.unit_convert(Q(1, {"m": 1}), "xyz")


def test_unit_convert_shows_whole_powers():
    assert str(Q.unit_convert(Q(1, {"N": 1}), "kg*m/s^2")) == "1.0 kg*m/s^2"


@pytest.mark.xfail(reason="volume in units.csv is based on l, so cm^3 (a length cubed) can't become ml")
def test_cubic_centimetres_to_millilitres():
    assert Q.unit_convert(Q(1, {"cm": 3}), "ml").value == pytest.approx(1)


# --- loading and updating the table ---

HEADER = ",unit,,ratiotosi,dimension_dict\n"


def use_table(monkeypatch, path):
    monkeypatch.setattr(quantity, "CACHE_FILE", path)
    quantity._cache.update(df=None, unit_data=None)


def test_downloaded_table_is_used_first(tmp_path, monkeypatch):
    table = tmp_path / "units.csv"
    table.write_text(HEADER + ',furlong,,201.168,"{""m"":1}"\n', encoding="utf-8")
    use_table(monkeypatch, table)
    assert quantity.lookup_unit("furlong")["factor"] == pytest.approx(201.168)


def test_bundled_table_used_when_nothing_downloaded(tmp_path, monkeypatch):
    use_table(monkeypatch, tmp_path / "missing.csv")
    assert "m" in quantity.retrive_units()


def test_bad_rows_are_skipped(tmp_path, monkeypatch):
    table = tmp_path / "units.csv"
    table.write_text(HEADER + "\n".join([
        ',ok,,"0,5","{""m"":1}"',        # comma as decimal point is fine
        ',,,1,"{""m"":1}"',              # no name
        ',nofactor,,abc,"{""m"":1}"',
        ',zero,,0,"{""m"":1}"',
        ',negative,,-1,"{""m"":1}"',
        ',baddict,,1,not a dict',
    ]) + "\n", encoding="utf-8")
    use_table(monkeypatch, table)
    assert quantity.retrive_units() == {"ok": {"factor": 0.5, "base_units": {"m": 1}}}


class FakeResponse:
    def __init__(self, content, status=200):
        self.content = content
        self.status = status

    def raise_for_status(self):
        if self.status != 200:
            raise requests.HTTPError(self.status)


@pytest.fixture
def cache_in_tmp(tmp_path, monkeypatch):
    monkeypatch.setattr(quantity, "CACHE_DIR", tmp_path)
    monkeypatch.setattr(quantity, "CACHE_FILE", tmp_path / "units.csv")
    return tmp_path / "units.csv"


def test_update_saves_downloaded_table(cache_in_tmp, monkeypatch):
    csv = (HEADER + ',m,,1,"{""m"":1}"\n').encode()
    monkeypatch.setattr(requests, "get", lambda *args, **kwargs: FakeResponse(csv))
    quantity.update_unit_file()
    assert cache_in_tmp.read_bytes() == csv


def no_connection(*args, **kwargs):
    raise requests.ConnectionError


@pytest.mark.parametrize("get", [
    no_connection,
    lambda *args, **kwargs: FakeResponse(b"", status=500),
    lambda *args, **kwargs: FakeResponse(b"<html>not a table</html>"),
])
def test_failed_update_keeps_old_table(cache_in_tmp, monkeypatch, get):
    cache_in_tmp.write_text("old")
    monkeypatch.setattr(requests, "get", get)
    quantity.update_unit_file()      # runs in a thread at startup, so it must never raise
    assert cache_in_tmp.read_text() == "old"
