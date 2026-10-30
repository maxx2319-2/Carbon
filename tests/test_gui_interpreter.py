import json

import pytest

pytest.importorskip("PySide6")
import gui


def results(latex):
    rows = json.loads(gui._InterpreterBridge().evaluate(json.dumps([latex])))
    return [row for kind, row in rows if kind == "result"]


@pytest.mark.parametrize("latex, expected", [
    (r"\mathrm{Løs}(x^2=2)", [r"\Rightarrow\:- \sqrt{2}", r"\Rightarrow\:\sqrt{2}"]),
    (r"\mathrm{Løs}(2x=1)", [r"\Rightarrow\:\frac{1}{2}"]),
    (r"\mathrm{SystemLøs}(Variabler=\{x,y\},x^2+y^2=4,x=y)", [
        r"\Rightarrow\:x = - \sqrt{2},\ y = - \sqrt{2}",
        r"\Rightarrow\:x = \sqrt{2},\ y = \sqrt{2}",
    ]),
])
def test_solutions_render_as_latex(latex, expected):
    assert results(latex) == expected


def test_numerisk_løs_stays_rounded():
    assert results(r"\mathrm{NumeriskLøs}(x^2=2,Variabel=x)") == [r"\Rightarrow\:\mathrm{1.41421}"]


def test_system_løs_no_solutions():
    assert results(r"\mathrm{SystemLøs}(Variabler=\{x\},x=1,x=2)") == [r"\Rightarrow\:\mathrm{Ingen\ løsninger}"]


@pytest.mark.parametrize("guess, expected", [
    ("", r"\Rightarrow\:x = \mathrm{0.0},\ y = \mathrm{3}"),
    (r",StartGæt=\{3,5\}", r"\Rightarrow\:x = \mathrm{2.70719},\ y = \mathrm{4.91451}"),
])
def test_numeric_system_løs_stays_rounded(guess, expected):
    latex = r"\mathrm{SystemLøs}\left(Variabler=\{x,y\},y=x^2-2x+3,y=3\cdot1.2^{x}" + guess + r"\right)"
    assert results(latex) == [expected]


def test_løs_interval_shows_every_solution():
    latex = r"\mathrm{Løs}\left(x^2-2x+3=3\cdot1.2^{x},Interval=\left(-50,50\right)\right)"
    assert results(latex) == [r"\Rightarrow\:\mathrm{0.0}", r"\Rightarrow\:\mathrm{2.70719}", r"\Rightarrow\:\mathrm{31.4646}"]
