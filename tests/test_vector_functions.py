import os
import re

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
import sympy

import gui
import interpreter


def run(*latex):
    ev = interpreter.EV()
    out = ev.ev("\n".join(gui.Latex_to_calc(l) for l in latex))
    return [str(v) for v in out.values()]


def numbers(s):
    return [float(x) for x in re.findall(r"-?\d+(?:\.\d+)?(?:e-?\d+)?", s)]


A = r"\overrightarrow{a}=\left\lbrace1.0000,2.0000\right\rbrace"
B = r"\overrightarrow{b}=\left\lbrace3.0000,1.0000\right\rbrace"


@pytest.mark.parametrize("latex, expected", [
    (r"\overrightarrow{\mathnormal{e}}_{\overrightarrow{a}}", [0.4472135955, 0.894427191]),
    (r"\hat{a}", [-2, 1]),
    (r"\!\overrightarrow{\:\hat{a}}", [-2, 1]),
    (r"\overset{\text{\^}}{\overrightarrow{a}}", [-2, 1]),
    (r"\overset{\text{\^{}}}{\overrightarrow{a}}", [-2, 1]),
    (r"\overrightarrow{b}_{\overrightarrow{a}}", [1, 2]),
    (r"{\overrightarrow{\mathnormal{e}}}_{\overrightarrow{a}}", [0.4472135955, 0.894427191]),
    (r"{\overrightarrow{b}}_{\overrightarrow{a}}", [1, 2]),
    (r"\angle(\overrightarrow{a},\overrightarrow{b})", [45]),
    (r"\operatorname{Det}(\overrightarrow{a},\overrightarrow{b})", [-5]),
])
def test_vector_function(latex, expected):
    out = run(A, B, latex)
    assert numbers(out[-1]) == pytest.approx(expected, rel=1e-4), out


def test_custom_function_definition():
    ev = interpreter.EV()
    out = ev.ev("x = 2+3\nf(x) = x^2+2x\ng(x, y) = Sin(x)*y")
    assert [str(v) for v in out.values()] == ["5.0", "Eq(f(x), x**2 + 2*x)", "Eq(g(x, y), y*Sin(x))"]
    assert sympy.latex(list(out.values())[1]) == r"f{\left(x \right)} = x^{2} + 2 x"
    assert ev.custom_funcsions["f"](3) == 15
    assert ev.custom_funcsions["g"](30, 2) == pytest.approx(1)
