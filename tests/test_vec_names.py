import pytest

import interpreter
from gui import Latex_to_calc, calc_to_latex, latex_text


@pytest.mark.parametrize("latex, expected", [
    (r"\vec{v}=\left\lbrace1,2,3\right\rbrace", "v_vec={1,2,3}"),
    (r"\vec{a}\times\vec{b}", "a_vec×b_vec"),
    (r"\vec{a}\cdot\vec{b}", "a_vec*b_vec"),
    (r"\vec{v_{1}}", "v1_vec"),
    (r"x+\vec{x}", "x+x_vec"),
    (r"\overrightarrow{v}=\left\lbrace1,2,3\right\rbrace", "v_vec={1,2,3}"),
    (r"\overrightarrow{a}\times\overrightarrow{b}", "a_vec×b_vec"),
    (r"\overrightarrow{a}\cdot\overrightarrow{b}", "a_vec*b_vec"),
])
def test_vec_becomes_its_own_name(latex, expected):
    assert Latex_to_calc(latex) == expected


def test_x_and_vec_x_are_different_variables():
    ev = interpreter.EV()
    lines = [r"x=5", r"\overrightarrow{x}=\left\lbrace1,2,3\right\rbrace", "x", r"\overrightarrow{x}"]
    out = ev.ev("\n".join(Latex_to_calc(l) for l in lines))
    assert str(out[2]) == "5.0"
    assert str(out[3]) == str(ev.variables["x_vec"].value)
    assert ev.variables["x_vec"].var_type == "list"


def test_cross_product_with_arrows():
    ev = interpreter.EV()
    lines = [
        r"\overrightarrow{a}=\left\lbrace1,0,0\right\rbrace",
        r"\overrightarrow{b}=\left\lbrace0,1,0\right\rbrace",
        r"\overrightarrow{a}\times\overrightarrow{b}",
    ]
    out = ev.ev("\n".join(Latex_to_calc(l) for l in lines))
    expected = interpreter.EV().ev("a={1,0,0}\nb={0,1,0}\na×b")[2]
    assert str(out[2]) == str(expected)


@pytest.mark.parametrize("raw", [r"2\cdot x\_vec", "2*x_vec"])
def test_results_show_the_arrow(raw):
    latex = calc_to_latex(raw)
    assert r"\overrightarrow{x}" in latex
    assert "vec" not in latex.replace(r"\overrightarrow", "")


def test_errors_show_the_arrow():
    latex = latex_text("Error: Ukendt variabel x_vec")
    assert latex == r"\text{Error: Ukendt variabel }\overrightarrow{\text{x}}"


def test_errors_without_vectors_are_unchanged():
    assert latex_text("Error: x_1 fejl") == r"\text{Error: x\_1 fejl}"
