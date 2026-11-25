import pytest
from interpreter import EV
from quantity import quantity

def run(*lines):
    return EV().ev("\n".join(lines))

def test_speed():
    out = run("Løs(x*2[s] = 10[m])")
    assert [str(q) for q in out[0]] == ["5.0 m/s"]

def test_square():
    out = run("Løs(x^2 = 4[m^2])")
    assert sorted(q.value for q in out[0]) == [-2.0, 2.0]

def test_constant():
    out = run("Løs(x*2[s] = 𝑔*4[s^2])")
    assert out[0][0] == quantity.create_quantity(19.64, "m/s")

def test_variable():
    out = run("t = 2[s]", "Løs(x*t = 10[m])")
    assert str(out[1][0]) == "5.0 m/s"

def test_mixed():
    out = run("Løs(x + 3[s] = 2[m])")
    assert "Enhederne passer ikke sammen" in out[0]

def test_no_unknown_mismatch():
    out = run("Løs(3[s] = 2[m])")
    assert "Enhederne passer ikke sammen" in out[0]

def test_unitless_unchanged():
    out = run("Løs(x^2 = 2)")
    assert [str(s) for s in out[0]] == ["-sqrt(2)", "sqrt(2)"]

def test_false():
    assert run("Løs(2 = 3)")[0] == "Ingen løsninger"

def test_interval_units():
    out = run("Løs(x*2[s] = 10[m], Interval = (0, 10))")
    assert "Interval kan ikke bruges med enheder endnu" in out[0]

def test_two_unknowns():
    out = run("Løs(x + y = 3)")
    assert [str(d) for d in out[0]] == ["{x: 3 - y}"]
