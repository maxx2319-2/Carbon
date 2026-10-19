# The pure functions in gui_old.py that translate between the MathLive editor and the interpreter.
import json

import pytest

pytest.importorskip("PySide6")
import gui_old as gui


# --- LaTeX from the editor -> interpreter text ---

@pytest.mark.parametrize("latex, expected", [
    (r"\frac{1}{2}", "((1)/(2))"),
    (r"\frac12", "((1)/(2))"),
    (r"\frac{x}2", "((x)/(2))"),
    (r"\frac{\frac{1}{2}}{3}", "((((1)/(2)))/(3))"),
    (r"\frac{1\lbrack m\rbrack}{2\lbrack s\rbrack}", "((1[m])/(2[s]))"),
    (r"\frac{1}{2}\lbrack m\rbrack", "((1)/(2))[m]"),
])
def test_fractions(latex, expected):
    assert gui.Latex_to_calc(latex) == expected


@pytest.mark.parametrize("latex, expected", [
    (r"x^2", "x^2"),
    (r"x^{2}", "x^2"),
    (r"x^{-1}", "x^-1"),
    (r"Fe^{3+}", "Fe^3+"),          # charges stay without parentheses
    (r"SO_4^{2-}", "SO4^2-"),
    (r"x^{ab}", "x^(ab)"),          # anything else gets parentheses
    (r"H_2O", "H2O"),
    (r"H_{2}O", "H2O"),
])
def test_powers_and_subscripts(latex, expected):
    assert gui.Latex_to_calc(latex) == expected


@pytest.mark.parametrize("latex, expected", [
    (r"1\lbrack m\rbrack", "1[m]"),
    (r"1\left\lbrack m\right\rbrack", "1[m]"),
    (r"1\lbrack\ m\ \rbrack", "1[m]"),
    (r"1\lbrack m\rbrack\rbrack", "1[m]"),
    (r"10\mu m", "10µm"),
])
def test_units(latex, expected):
    assert gui.Latex_to_calc(latex) == expected


@pytest.mark.parametrize("latex, expected", [
    (r"2\cdot3", "2*3"),
    (r"2\times3", "2*3"),
    (r"\left(1+2\right)\cdot3", "(1+2)*3"),
    (r"H_2+O_2\to H_2O", "H2+O2->H2O"),
    (r"A\longrightarrow B", "A->B"),
    (r"50\%", "50%"),
    (r"\#kommentar", "#kommentar"),
    (r"x\:=\:5", "x = 5"),
    (r"x\,=\,5", "x = 5"),
    (r"x=^{\prime}abc^{\prime}", "x='abc'"),
    (r"DNA\_til", "DNA_til"),       # a typed underscore, not a subscript
    (r"  1+1  ", "1+1"),
    (r"v=\{1,2,3\}", "v={1,2,3}"),
    (r"v=\left\{1,2,3\right\}", "v={1,2,3}"),
    (r"v=\lbrace1,2,3\rbrace", "v={1,2,3}"),
    (r"v=\left\lbrace1,2,3\right\rbrace", "v={1,2,3}"),
])
def test_symbols(latex, expected):
    assert gui.Latex_to_calc(latex) == expected


@pytest.mark.parametrize("latex, expected", [
    (r"\textcolor{#569CD6}{\mathbf{pH}}\left(4,2\right)", "pH(4,2)"),
    (r"\textcolor{#B5CEA8}{4}", "4"),
    (r"v=\textcolor{#B5CEA8}{\{1,2\}}", "v={1,2}"),
    (r"\mathrm{kg}", "kg"),
    (r"\text{hej}", "hej"),
    (r"\operatorname{pH}(1,2)", "pH(1,2)"),
])
def test_highlighting_is_removed(latex, expected):
    assert gui.Latex_to_calc(latex) == expected


def test_rightarrow():
    assert gui.Latex_to_calc(r"H_2+O_2\rightarrow H_2O") == "H2+O2->H2O"


# --- interpreter result -> LaTeX for the output pane ---

@pytest.mark.parametrize("text, expected", [
    ("2.0", r"\mathrm{2.0}"),
    (2.9, r"\mathrm{2.9}"),
    ("0.5 m/s", r"\mathrm{0.5\ m/s}"),
    ("kg*m/s^2", r"\mathrm{kg\cdot\ m/s^2}"),
    ("H2O", r"\mathrm{H_{2}O}"),
    ("2H2 + O2 -> 2H2O", r"\mathrm{2H_{2}\ +\ O_{2}\ \to\ \ 2H_{2}O}"),
    ("1.23456789", r"\mathrm{1.23457}"),            # long decimals are cut to 6 digits
    ("1e-05", r"\mathrm{1\cdot{10}^{-5}}"),
    ("2.5e+10", r"\mathrm{2.5\cdot{10}^{10}}"),
    ("1.234567891e-05", r"\mathrm{1.23457\cdot{10}^{-5}}"),
    ("MnO4^-", r"\mathrm{MnO_{4}^-}"),
])
def test_calc_to_latex(text, expected):
    assert gui.calc_to_latex(text) == expected


@pytest.mark.xfail(reason="the + in a charge like ^2+ isn't put in braces, so only the 2 is raised")
def test_calc_to_latex_charge():
    assert "^{2+}" in gui.calc_to_latex("Fe^2+")


@pytest.mark.parametrize("text, expected", [
    ("Error: x", r"\text{Error: x}"),
    ("a_b", r"\text{a\_b}"),
    ("50%", r"\text{50\%}"),
    ("{x}", r"\text{\{x\}}"),
    ("a#b", r"\text{a\#b}"),
    ("x^2", r"\text{x\^{}2}"),
    ("\\", r"\text{\backslash }"),
    ("~&$", r"\text{\~{}\&\$}"),
])
def test_latex_text_escapes(text, expected):
    assert gui.latex_text(text) == expected


# --- the whole Regneark round trip ---

def run_sheet(*lines):
    return json.loads(gui._MapleBridge().run(json.dumps(list(lines))))


def test_sheet_result():
    assert run_sheet("1+1") == [["code", "1+1"], ["result", r"\Rightarrow\:\mathrm{2.0}"]]


def test_sheet_error():
    assert run_sheet("1+") == [["code", "1+"], ["error", r"\Rightarrow\:\text{Error: interpreter}"]]


def test_sheet_fraction_with_units():
    rows = run_sheet(r"\frac{1\lbrack m\rbrack}{2\lbrack s\rbrack}")
    assert rows[1] == ["result", r"\Rightarrow\:\mathrm{0.5\ m/s}"]


def test_sheet_variables():
    assert run_sheet("x=5", r"x\cdot2") == [
        ["code", "x=5"],
        ["code", r"x\cdot2"],
        ["result", r"\Rightarrow\:\mathrm{10.0}"],
    ]


def test_sheet_coloured_function_call():
    rows = run_sheet(r"\textcolor{#569CD6}{\mathbf{Afstem}}\left(H_2+O_2\to H_2O\right)")
    assert rows[1] == ["result", r"\Rightarrow\:\mathrm{2H_{2}\ +\ O_{2}\ \to\ \ 2H_{2}O}"]


def test_sheet_multi_line_result():
    rows = run_sheet(r"Help\left(\right)")
    assert [kind for kind, _ in rows] == ["code"] + ["result"] * len(gui.interpreter_maple.EV().functions)


@pytest.mark.parametrize("line", [r"\#hej", ""])
def test_sheet_line_without_output(line):
    assert run_sheet(line) == [["code", line]]


def test_empty_sheet():
    assert run_sheet() == []
