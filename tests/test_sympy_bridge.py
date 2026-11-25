import sympy
import pytest
from quantity import quantity
from interpreter import _Quantity_to_Sympy_Bridge as to_s, _Sympy_to_Quantity_Bridge as to_q, DIMENSION_SYMBOLS as D

L, T = D["L"], D["T"]

def test_q_to_s_unit():
    assert sympy.simplify(to_s(quantity.create_quantity(12, "m/s")) - 12*L/T) == 0

def test_q_to_s_km():
    assert sympy.simplify(to_s(quantity.create_quantity(3, "km")) - 3000*L) == 0

def test_q_to_s_unitless():
    assert to_s(quantity(5, {}, {})) == 5

def test_s_to_q_unit():
    q = to_q(5*L/T)
    assert q.value == 5 and q.dimension == {"L": 1.0, "T": -1.0} and q.current_units == {"m": 1.0, "s": -1.0}

def test_s_to_q_unitless():
    q = to_q(sympy.Integer(7))
    assert q.value == 7 and q.dimension == {}

def test_s_to_q_mixed():
    with pytest.raises(ValueError, match="Enhederne passer ikke sammen"):
        to_q(3*T - 2*L)

def test_s_to_q_symbolic():
    x = sympy.Symbol("x")
    q = to_q(5*x*L/T)
    assert q.value == 5*x and q.dimension == {"L": 1.0, "T": -1.0}

def test_roundtrip():
    q = to_q(to_s(quantity.create_quantity(2, "N")))
    assert q == quantity.create_quantity(2, "N")
