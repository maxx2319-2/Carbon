import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
import sympy

import gui
import interpreter


def last(*latex):
    out = interpreter.EV().ev("\n".join(gui.Latex_to_calc(l) for l in latex))
    return list(out.values())[-1]


x, t = sympy.symbols("x t")


@pytest.mark.parametrize("defs, line, expected", [
    (["a=5"], r"\lim_{h\to0}\left(a+h\right)", 5),
    (["abc=2"], r"\lim_{h\to0}\left(abc+h\right)", 2),
    (["v_0=12"], r"\lim_{h\to0}\left(v_0+h\right)", 12),
    (["x=2", "t=3"], r"\frac{\differentialD}{\differentialD x}\left(x^2 t\right)", 6 * x),
    (["x=2", "t=3"], r"\frac{\differentialD}{\differentialD t}\left(x^2 t\right)", 4),
    (["x=2", "t=3"], r"\int x t\,\differentialD x", sympy.Rational(3, 2) * x**2),
    (["x=2", "t=3"], r"\int x t\,\differentialD t", t**2),
    (["x=2", "t=3"], r"\int_0^2 x t\,\differentialD x", 6),
    (["n=4"], r"\sum_{k=1}^{n}\left(k\right)", 10),
    (["d=1/3"], r"\int_0^3 d x\,\differentialD x", sympy.Rational(3, 2)),
])
def test_variables_are_substituted_except_the_bound_one(defs, line, expected):
    assert sympy.simplify(last(*defs, line) - expected) == 0


@pytest.mark.parametrize("defs", [[r"b=3\ m"], [r"b=\{1,2\}"]])
def test_unit_and_vector_variables_give_error(defs):
    assert last(*defs, r"\lim_{h\to0}\left(b+h\right)") == "Error: b skal være et tal uden enhed for at kunne bruges her"
