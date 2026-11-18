import math
import os
import re

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

import gui
import interpreter


SETUP = ["a={1,2,3}", "b={4,5,6}", "c={1,2}", "d={3,4}", "k=2"]


def run(*lines):
    out = interpreter.EV().ev("\n".join(SETUP + list(lines)))
    return str(out[len(SETUP) + len(lines) - 1])


def run_latex(latex):
    v = r"\vec{%s}=\left\lbrace %s\right\rbrace"
    lines = [v % ("a", "1,2,3"), v % ("b", "4,5,6"), latex]
    out = interpreter.EV().ev("\n".join(gui.Latex_to_calc(l) for l in lines))
    return str(out[2])


def numbers(s):
    return [float(x) for x in re.findall(r"-?\d+(?:\.\d+)?(?:e-?\d+)?", s)]


@pytest.mark.parametrize("line, expected", [
    ("a+b", [5, 7, 9]),
    ("a-b", [-3, -3, -3]),
    ("a+b+a", [6, 9, 12]),
    ("a+b-a", [4, 5, 6]),
    ("2a", [2, 4, 6]),
    ("2*a", [2, 4, 6]),
    ("a*2", [2, 4, 6]),
    ("k*a", [2, 4, 6]),
    ("a*k", [2, 4, 6]),
    ("0.5*a", [0.5, 1, 1.5]),
    ("((1)/(2))*a", [0.5, 1, 1.5]),
    ("a/2", [0.5, 1, 1.5]),
    ("-a", [-1, -2, -3]),
    ("(a+b)*2", [10, 14, 18]),
    ("2(a+b)", [10, 14, 18]),
    ("3*a+b", [7, 11, 15]),
    ("a*b", [32]),
    ("a*b+1", [33]),
    ("a*b*2", [64]),
    ("a×b", [-3, 6, -3]),
    ("2a×b", [-6, 12, -6]),
    ("(a+b)×a", [3, -6, 3]),
    ("(a×b)*a", [0]),
    ("Abs(a)", [math.sqrt(14)]),
    ("Abs(a+b)", [math.sqrt(155)]),
    ("Abs(a)*2", [2 * math.sqrt(14)]),
    ("Abs(c)^2", [5]),
    ("a+{1,1,1}", [2, 3, 4]),
    ("{1,2,3}+{1,1,1}", [2, 3, 4]),
    ("{1/2, 3}", [0.5, 3]),
    ("EnhedsVektor(c)", [1 / math.sqrt(5), 2 / math.sqrt(5)]),
    ("EnhedsVektor(a+b)", [5 / math.sqrt(155), 7 / math.sqrt(155), 9 / math.sqrt(155)]),
    ("VinkelVektor(a,b)", [12.933154491899135]),
    ("VinkelVektor(c,d)", [10.304846468766]),
    ("Projektion(b,a)", [32 / 14, 64 / 14, 96 / 14]),
    ("TværVektor(c)", [-2, 1]),
    ("Det(c,d)", [-2]),
    ("2×3", [6]),
])
def test_vector_calculation(line, expected):
    out = run(line)
    assert numbers(out) == pytest.approx(expected, rel=1e-6), out


@pytest.mark.parametrize("line", ["-{4,0,6}", "-2*{0,1}", "{0,1}*(-1)"])
def test_no_negative_zero(line):
    assert "-0.0" not in run(line), run(line)


def test_angle_has_no_degree_symbol_and_can_be_reused():
    assert "°" not in run("VinkelVektor(a,b)")
    assert numbers(run("θ=VinkelVektor(a,b)", "θ+1")) == pytest.approx([13.933154491899135])


@pytest.mark.parametrize("lines, expected", [
    (["e=a+b", "e"], [5, 7, 9]),
    (["e=2a", "e*b"], [64]),
    (["e=a", "e+=b", "e"], [5, 7, 9]),
    (["e=a", "e-=b", "e"], [-3, -3, -3]),
    (["l=Abs(c)", "l^2"], [5]),
])
def test_vector_results_can_be_stored(lines, expected):
    assert numbers(run(*lines)) == pytest.approx(expected), run(*lines)


@pytest.mark.parametrize("line, error", [
    ("a+c", "Error: vektorerne skal have samme længde"),
    ("a*c", "Error: vektorerne skal have samme længde"),
    ("VinkelVektor(a,c)", "Error: vektorerne skal have samme længde"),
    ("a+1", "Error: man kan ikke bruge + eller - mellem et tal og en vektor"),
    ("1/a", "Error: man kan ikke dividere med en vektor"),
    ("a/b", "Error: man kan ikke dividere med en vektor"),
    ("2[m]*a", "Error: en vektor kan ikke have enheder"),
    ("{2[m],3}", "Error: en vektor kan ikke have enheder"),
    ("{1,{2}}", "Error: en vektor kan ikke indeholde en vektor"),
    ("a^2", "Error: en vektor kan ikke opløftes i en potens"),
    ("Sin(a)", "Error: Sin kan ikke tage imod en vektor"),
    ("EnhedsVektor(2)", "Error: EnhedsVektor skal have vektorer"),
    ("a×c", "Error: du kan kun lave kryds product med 3d vektorer"),
])
def test_vector_errors_are_danish(line, error):
    assert run(line) == error


@pytest.mark.parametrize("latex, expected", [
    (r"2\vec{a}", [2, 4, 6]),
    (r"-\vec{a}", [-1, -2, -3]),
    (r"\frac{1}{2}\vec{a}", [0.5, 1, 1.5]),
    (r"0.5\cdot\vec{a}", [0.5, 1, 1.5]),
    (r"\left|\vec{a}+\vec{b}\right|", [math.sqrt(155)]),
    (r"\vec{a}\cdot\vec{b}+1", [33]),
    (r"2\vec{a}\times\vec{b}", [-6, 12, -6]),
    (r"\angle(\vec{a},\vec{b})", [12.933154491899135]),
])
def test_vector_latex(latex, expected):
    out = run_latex(latex)
    assert numbers(out) == pytest.approx(expected, rel=1e-6), out


def test_times_still_works_in_sympy_functions():
    out = interpreter.EV().ev("Løs(2×x=4)")
    assert numbers(str(out[0])) == [2], out
