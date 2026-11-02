import json
import os
import random
import subprocess
import sys
from pathlib import Path

import pytest

import interpreter

SRC = Path(__file__).resolve().parent.parent / "src"

PRELUDE = (
    "import os, sys, json, time\n"
    "import quantity\n"
    "quantity.CACHE_FILE = quantity.BUNDLED_FILE\n"
    "import interpreter\n"
    "def ev(text):\n"
    "    return interpreter.EV().ev(text)\n"
)


def isolated(code, timeout):
    env = {**os.environ, "MPLBACKEND": "agg", "QT_QPA_PLATFORM": "offscreen", "PYTHONIOENCODING": "utf-8", "PYTHONHASHSEED": "0"}
    try:
        proc = subprocess.run([sys.executable, "-c", PRELUDE + code], cwd=SRC, env=env,
                              capture_output=True, text=True, encoding="utf-8", timeout=timeout)
    except subprocess.TimeoutExpired:
        return None
    assert proc.returncode == 0, proc.stderr[-2000:]
    return json.loads(proc.stdout.strip().splitlines()[-1])


def ev(text):
    return interpreter.EV().ev(text)


TOKENS = [
    "1", "2", "3.5", "0", "10", "1e308", "-", "+", "*", "/", "^", "(", ")", "(", ")", " ", "x", "y", "a", "π", "e",
    "[m]", "[km]", "[g/mol]", "[km/t]", "[°C]", "[", "]", "=", "+=", "-=", ",", "{", "}", "'", '"', "#",
    "Sin(", "Ln(", "Exp(", "Round(", "sqrt(", "Abs(", "Gamma(", "Log(", "ArcSin(",
    "->", "<->", "H2O", "Ca(OH)2", "^2+", "ATG", "syre", "Interval = (", "Variabel = x", "{1,2,3}",
]

FUNCTION_HEADS = [
    "pH(", "pOH(", "Afstem(", "Analyse(", "EnhedKonvertering(", "MængdeBeregning(", "Puffer(", "Help(",
    "UdbytteProcent(", "MasseProcent(", "DNATilPeptid(", "pHTilKoncentration(", "BjerrumDiagram(",
    "LinReg(", "ExpReg(", "Regression(", "PlotFunktion(", "Simplificer(", "Løs(", "NumeriskLøs(", "Loop(",
]


def fuzz_lines(seed, count):
    rng = random.Random(seed)
    out = []
    for _ in range(count):
        body = "".join(rng.choice(TOKENS) for _ in range(rng.randint(1, 12)))
        if rng.random() < 0.35:
            body = rng.choice(FUNCTION_HEADS) + body + ")"
        out.append(body)
    return out


@pytest.mark.parametrize("seed", range(4))
def test_fuzzed_sheet_never_raises_and_finishes(seed):
    lines = fuzz_lines(seed, 400)
    result = isolated(
        "lines = " + repr(lines) + "\n"
        "bad = []\n"
        "for line in lines:\n"
        "    try:\n"
        "        ev(line)\n"
        "    except BaseException as e:\n"
        "        bad.append([line, type(e).__name__])\n"
        "print(json.dumps(bad))\n",
        timeout=240,
    )
    assert result is not None, "a fuzzed sheet did not finish within 240 s"
    assert result == []


@pytest.mark.parametrize("text", [
    "(" * 1000 + "1" + ")" * 1000,
    "2^" * 2000 + "2",
    "1e400 - 1e400",
    "9^9^9",
    "10^309",
    "😀+1\n\u202e2+2\n\x00\n\ufeff3",
    "=",
    "#",
    "a" * 100000 + " = 5",
], ids=["parens-1000", "power-tower-2000", "inf-minus-inf", "9^9^9", "10^309", "unicode-junk", "only-equals", "only-hash", "name-100k"])
def test_extreme_input_gives_an_answer_or_an_error(text):
    out = ev(text)
    assert all(isinstance(k, int) for k in out)


def test_200k_term_sum_finishes():
    result = isolated("t = time.perf_counter()\nr = ev('1+' * 200000 + '1')\nprint(json.dumps([str(r[0]), time.perf_counter() - t]))", 120)
    assert result is not None
    assert result[0] == "200001.0"
    assert result[1] < 20


def test_20000_lines_finish():
    result = isolated("t = time.perf_counter()\nr = ev('\\n'.join('1+1' for _ in range(20000)))\nprint(json.dumps([len(r), time.perf_counter() - t]))", 120)
    assert result is not None
    assert result[0] == 20000
    assert result[1] < 30


def test_100k_loop_iterations_finish():
    result = isolated("t = time.perf_counter()\nr = ev('x = 0\\nx += 1\\nLoop(2,2,100000)')\nprint(json.dumps([len(r[2]), time.perf_counter() - t]))", 120)
    assert result is not None
    assert result[0] == 100000
    assert result[1] < 30


@pytest.mark.xfail(reason="P-02: the variable regex is rebuilt after every assignment, so n variables cost O(n^2)", strict=True)
def test_2000_variables_finish_quickly():
    result = isolated("t = time.perf_counter()\nr = ev('\\n'.join(f'v{i} = {i}' for i in range(2000)) + '\\nv1999 + 1')\nprint(json.dumps([str(r[2000]), time.perf_counter() - t]))", 90)
    assert result is not None
    assert result[0] == "2000.0"
    assert result[1] < 3


@pytest.mark.xfail(reason="C-03: Loop has no upper limit and a running calculation can't be cancelled", strict=True)
def test_huge_loop_count_is_refused_or_finishes():
    assert isolated("ev('x = 0\\nx += 1\\nLoop(2,2,100000000)')\nprint('[]')", 30) is not None


@pytest.mark.xfail(reason="C-03: symbolic functions have no time limit", strict=True)
def test_exact_harmonic_sum_has_a_time_limit():
    assert isolated("ev('summation(1/k, (k, 1, 100000))')\nprint('[]')", 45) is not None


@pytest.mark.xfail(reason="C-04: the ThreadPool used for the 20 s SystemLøs limit keeps computing in the background", strict=True)
def test_systemløs_timeout_does_not_leave_a_thread_running():
    result = isolated(
        "import threading\n"
        "ev('SystemLøs(x^7 + y^3 = 1, Cos(x)*y = Sin(y), Variabler = {x, y})')\n"
        "time.sleep(2)\n"
        "print(json.dumps(threading.active_count()))\n",
        120,
    )
    assert result == 1


@pytest.mark.xfail(reason="S-01: calculus lines go straight into sympy's parse_expr, which evaluates them as Python", strict=True)
def test_calculus_line_cannot_call_python_builtins():
    assert str(ev("integrate(x, x) + len('abcd')")[0]).startswith("Error")


@pytest.mark.xfail(reason="B-01: prep_sympy uses SYMPY_GLOBALS, which doesn't exist", strict=True)
@pytest.mark.parametrize("text", ["Simplificer(sqrt(12) + sqrt(27))", "Løs(sqrt(x) = 2)", "PlotFunktion(sqrt(x))"])
def test_sqrt_works_in_symbolic_functions(text):
    assert not str(ev(text)[0]).startswith("Error")


@pytest.mark.xfail(reason="B-02: exclude_loops compares the name with 'loop', so loop lines also run once outside the loop", strict=True)
def test_loop_runs_its_lines_exactly_count_times():
    assert str(ev("x = 0\nx += 1\nLoop(2,2,3)\nx")[3]) == "3.0"


@pytest.mark.xfail(reason="B-03: a variable is only replaced between word boundaries, so 2x stays the unit x", strict=True)
def test_number_times_variable():
    assert str(ev("x = 5\n2x")[1]) == "10.0"


@pytest.mark.xfail(reason="B-03: the variable's text is pasted in without parentheses", strict=True)
@pytest.mark.parametrize("text, expected", [
    ("a = -2\n3 a", "-6.0"),
    ("v = 2[m/s]\n10/v", "5.0 s/m"),
])
def test_variable_is_used_as_one_value(text, expected):
    assert str(ev(text)[1]) == expected


@pytest.mark.xfail(reason="B-04: any text before = becomes a variable name, even a number", strict=True)
def test_a_number_cannot_become_a_variable():
    out = ev("2 = 5\n2+2")
    assert str(out[0]).startswith("Error") and str(out[1]) == "4.0"


@pytest.mark.xfail(reason="B-05: plain calculations never convert units, so km and m can't be added", strict=True)
@pytest.mark.parametrize("text", ["1[km] + 500[m]", "1[kg] - 200[g]"])
def test_adding_the_same_kind_of_unit(text):
    assert not str(ev(text)[0]).startswith("Error")


@pytest.mark.xfail(reason="B-06: parser.atom rounds every function result to config.rounding_decimals", strict=True)
@pytest.mark.parametrize("text, expected", [
    ("Exp(-10)", 4.54e-5),
    ("Sin(1)*1000", 17.452),
    ("Ln(2)*100", 69.315),
    ("Round(3.14159, 3)", 3.142),
])
def test_function_results_keep_their_precision(text, expected):
    assert ev(text)[0].value == pytest.approx(expected, rel=1e-4)


@pytest.mark.xfail(reason="B-19: Round uses Python's round half to even", strict=True)
def test_round_rounds_halves_up():
    assert ev("Round(2.5)")[0].value == 3


@pytest.mark.xfail(reason="M-01: π and e are read as units", strict=True)
@pytest.mark.parametrize("text, expected", [("2π", 6.2832), ("e^2", 7.3891)])
def test_constants_are_numbers(text, expected):
    assert ev(text)[0].value == pytest.approx(expected, rel=1e-4)


@pytest.mark.xfail(reason="B-07: Help() only looks in error_text, which has no maths functions", strict=True)
@pytest.mark.parametrize("name", ["Ln", "Sin", "Round"])
def test_help_for_maths_functions(name):
    assert not str(ev(f"Help({name})")[0]).startswith("Error")


@pytest.mark.xfail(reason="B-08: `variables` is only set when a Variabler= part exists", strict=True)
def test_systemløs_without_variabler_explains_the_syntax():
    assert ev("SystemLøs(x+y=2, x-y=0, z=1)")[0] == "Error: " + interpreter.EV().error_text["SystemLøs"]


@pytest.mark.xfail(reason="B-09: MængdeBeregning keys aren't stripped and values can't be variables", strict=True)
@pytest.mark.parametrize("text", ["MængdeBeregning(m = 10[g], M = 58.44[g/mol])", "masse = 10\nMængdeBeregning(m=masse, M=58.44)"])
def test_mængdeberegning_accepts_spaces_and_variables(text):
    assert "Stofmængde" in str(ev(text)[text.count("\n")])


@pytest.mark.xfail(reason="B-10: m^3 is parsed as metre cubed, but litre is its own base unit", strict=True)
def test_cubic_metres_to_litres():
    assert ev("EnhedKonvertering(1[m^3], l)")[0].value == pytest.approx(1000)


@pytest.mark.xfail(reason="B-11: unknown parts of the target unit are skipped silently", strict=True)
def test_unknown_target_unit_is_an_error():
    assert str(ev("EnhedKonvertering(5[km], mxyz)")[0]).startswith("Error")


@pytest.mark.xfail(reason="B-12: procent re-parses str(quantity), so compound units are split up", strict=True)
def test_masseprocent_with_compound_units():
    assert ev("MasseProcent(2[g/l], 4[g/l])")[0] == "50%"


@pytest.mark.xfail(reason="B-13: BjerrumDiagram doesn't strip the names, so ' carbonsyre' is read as a unit", strict=True)
def test_bjerrum_names_after_a_space():
    assert not isinstance(ev("BjerrumDiagram(ethansyre, carbonsyre)")[0], str)


@pytest.mark.xfail(reason="B-14: lowercase or empty formulas give molar mass 0 instead of an error", strict=True)
def test_analyse_rejects_a_formula_without_elements():
    assert str(ev("Analyse(co2)")[0]).startswith("Error")


@pytest.mark.xfail(reason="B-17: parentheses are ignored, so Afstem balances the wrong formulas and prints a wrong equation", strict=True)
def test_afstem_with_parentheses_is_right_or_an_error():
    out = str(ev("Afstem(K4Fe(CN)6 + KMnO4 + H2SO4 -> KHSO4 + Fe2(SO4)3 + MnSO4 + HNO3 + CO2 + H2O)")[0])
    assert out.startswith("Error") or out.startswith("10K4Fe(CN)6 + 122KMnO4 + 299H2SO4")


@pytest.mark.xfail(reason="B-20: the non-linear regressions start curve_fit from all ones", strict=True)
def test_harmonic_regression_finds_a_clean_sine():
    import math
    xs = [i * 0.25 for i in range(40)]
    ys = [2 * math.sin(3 * x + 0.5) + 1 for x in xs]
    fig = ev("HarmReg({" + ",".join(f"{x:.2f}" for x in xs) + "},{" + ",".join(f"{y:.4f}" for y in ys) + "})")[0]
    label = fig.axes[0].get_legend().get_texts()[0].get_text()
    r2 = float(label.split("R^2 = ")[1].split("$")[0])
    assert r2 > 0.99


@pytest.mark.xfail(reason="M-02: function calls only work as a whole line, so their result can't be stored", strict=True)
def test_function_result_in_a_variable():
    assert not str(ev("x = pH(4.76, 0.1)")[0]).startswith("Error")


@pytest.mark.xfail(reason="E-01: Python's own English error text reaches the user", strict=True)
@pytest.mark.parametrize("text", ["1/0", "Ln(-1)", "Exp(1000)", "10^309", "Loop(1,1,2.5)", "pH(4.76, 0)"])
def test_errors_are_in_danish(text):
    message = str(ev(text)[0])
    assert not any(word in message for word in ("division", "math domain", "math range", "Result too large", "invalid literal"))
