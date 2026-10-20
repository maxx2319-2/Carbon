import re
from pathlib import Path

import pytest
import interpreter_maple
from quantity import quantity



@pytest.fixture
def interpreter():
    inte = interpreter_maple.EV()
    return inte


# --- variables ---

@pytest.mark.parametrize("line, name, expected", [
    ("x = 1",       "x", "1.0 Quantity"),
    ("x= 1",        "x", "1.0 Quantity"),
    ("x =1",        "x", "1.0 Quantity"),
    ("x = 1[m]",    "x", "1.0 m Quantity"),
    ("x = 1+1",     "x", "2.0 Quantity"),
    ("x = 2[m]/1[s]", "x", "2.0 m/s Quantity"),
    ("y = slop",  "y", "slop str"),
    ('z = slop2', "z", "slop2 str"),
    ("z=slop2",   "z", "slop2 str"),
    ('s = a b',   "s", "a b str"),
    ("s = it\'s", "s", "it's str"),
    ])
def test_variable_save(interpreter, line, name, expected):
    interpreter.ev(line)
    assert str(interpreter.variables[name]) == expected


def test_assignment_gives_no_output(interpreter):
    assert interpreter.ev("x = 1") == {}


def test_reassigning_overwrites(interpreter):
    out = interpreter.ev("x = 1\nx = 2\nx")
    assert str(out[2]) == "2.0"


def test_variables_used_in_calculation(interpreter):
    out = interpreter.ev("v = 1[m]/2[s]\nt = 4[s]\nv*t")
    assert str(out[2]) == "2.0 m"


def test_variable_after_first_calc(interpreter):
    out = interpreter.ev("x = 2\nx+1\ny = 3\ny+1")
    assert str(out[1]) == "3.0"
    assert str(out[3]) == "4.0"


def test_longer_name_is_not_replaced_by_shorter(interpreter):
    out = interpreter.ev("x = 5\nxx = 2\nxx+x")
    assert str(out[2]) == "7.0"


def test_variable_not_replaced_inside_unit_brackets(interpreter):
    out = interpreter.ev("m = 5\n2[m]\nm*2")
    assert str(out[1]) == "2.0 m"
    assert str(out[2]) == "10.0"


def test_variables_are_kept_between_runs(interpreter):
    interpreter.ev("x = 1")
    assert str(interpreter.ev("x+1")[0]) == "2.0"


@pytest.mark.xfail(reason="the variable's text is pasted in without parentheses, so x^2 only squares the "
                          "unit or the minus sign is applied last; as_expr() in interpreter.py wraps it")
@pytest.mark.parametrize("text, expected", [
    ("x = 2[m]\nx^2", "4.0 m^2"),
    ("x = -2\nx^2", "4.0"),
    ("y = 2[m]/1[s]\n1/y", "0.5 s/m"),
])
def test_variable_keeps_its_value_together(interpreter, text, expected):
    assert str(interpreter.ev(text)[1]) == expected



def test_comment_with_equals_sign_is_ignored(interpreter):
    assert interpreter.ev("# a = 5") == {}
    assert interpreter.variables == {}



def test_assignment_without_name_is_an_error(interpreter):
    assert str(interpreter.ev("= 5")[0]).startswith("Error")


# --- plain calculations ---

@pytest.mark.parametrize("line, expected", [
    ("1 + 1", "2.0"),
    ("  1 + 1  ", "2.0"),
    ("(2 + 3)*4", "20.0"),
    ("2^3", "8.0"),
    ("1[m]/2[s]", "0.5 m/s"),
    ("2 [m]", "2.0 m"),
    ("((1[m])/(2[s]))", "0.5 m/s"),     # how Latex_to_calc writes a fraction
])
def test_parser(interpreter, line, expected):
    x = interpreter.ev(line)
    assert str(x[0]) == expected


def test_calculation_returns_a_quantity(interpreter):
    assert isinstance(interpreter.ev("1[m]")[0], quantity)


@pytest.mark.parametrize("text", ["# kommentar", "   # indrykket"])
def test_comment_gives_no_output(interpreter, text):
    assert interpreter.ev(text) == {}


def test_blank_lines_keep_line_numbers(interpreter):
    out = interpreter.ev("1 + 1\n\n\n2 + 2")
    assert list(out) == [0, 3]
    assert str(out[3]) == "4.0"


# --- errors ---

@pytest.mark.parametrize("line", ["1 +", "(2 + 3", "1/0", "x == 5", "x = ", "pH (4.76,0.10)"])
def test_bad_line_gives_error(interpreter, line):
    assert str(interpreter.ev(line)[0]).startswith("Error")


def test_error_does_not_stop_next_line(interpreter):
    out = interpreter.ev("1 +\n1 + 1")
    assert str(out[0]).startswith("Error")
    assert str(out[1]) == "2.0"


@pytest.mark.xfail(reason="the inner `except: raise ValueError(\"interpreter\")` hides the real message")
def test_error_shows_real_message(interpreter):
    out = interpreter.ev("(2 + 3")
    assert "Mangler ')'" in out[0]


@pytest.mark.xfail(reason="a name that isn't a function is read as a unit: ukendt(1) gives 1.0 ukendt")
def test_unknown_function(interpreter):
    assert str(interpreter.ev("ukendt(1)")[0]).startswith("Error")


def test_function_names_are_case_sensitive(interpreter):
    assert str(interpreter.ev("help()")[0]).startswith("Error")


# --- function list and help ---

FUNCTIONS = interpreter_maple.EV().functions
HELP_TEXT = interpreter_maple.EV().help_text
KNOWN_BAD_HELP = {"pOH": "the help text for pOH starts with pH("}


def test_functions_registered(interpreter):
    assert {"Help", "Afstem", "pH", "pOH","EnhedKonvertering"} <= set(interpreter.functions)


@pytest.mark.parametrize("name", [f for f in FUNCTIONS if f != "Help"])
def test_every_function_has_help_text(name):
    assert name in HELP_TEXT


@pytest.mark.parametrize("name", [
    pytest.param(f, marks=pytest.mark.xfail(reason=KNOWN_BAD_HELP[f])) if f in KNOWN_BAD_HELP else f
    for f in HELP_TEXT
])
def test_help_text_shows_how_to_call_the_function(name):
    assert HELP_TEXT[name].startswith(name + "(")


def test_editor_colours_the_same_functions():
    html = (Path(interpreter_maple.__file__).parent.parent / "Assets_math_live" / "regneark.html").read_text(encoding="utf-8")
    listed = re.search(r"const FUNCTIONS = \[(.*?)\]", html).group(1)
    assert set(re.findall(r'"([^"]+)"', listed)) == set(FUNCTIONS)


def test_help_lists_functions(interpreter):
    out = interpreter.ev("Help()")
    assert out[0].splitlines() == interpreter.functions


def test_help_for_function(interpreter):
    out = interpreter.ev("Help(pH)")
    assert out[0] == interpreter.help_text["pH"]


def test_help_unknown_function(interpreter):
    out = interpreter.ev("Help(foo)")
    assert out[0].startswith("Error: Ukendt function foo")
    assert "config.json" not in out[0]


# --- Afstem ---

@pytest.mark.parametrize("line, expected", [
    ("Afstem(H2+O2->H2O)", "2H2 + O2 -> 2H2O"),
    ("Afstem(H2 + O2 -> H2O)", "2H2 + O2 -> 2H2O"),
    ("Afstem(MnO4^- + Fe^2+ -> Mn^2+ + Fe^3+,syre)",
     "MnO4^- + 5Fe^2+ + 8H3O^+ -> 12H2O + Mn^2+ + 5Fe^3+"),
    ("Afstem(MnO4^- + I^- -> MnO2 + I2,base)",
     "2MnO4^- + 6I^- + 4H2O -> 8OH^- + 2MnO2 + 3I2"),
])
def test_afstem(interpreter, line, expected):
    assert interpreter.ev(line)[0] == expected


@pytest.mark.xfail(reason="the medium isn't stripped, so ' syre' is not recognised")
def test_afstem_space_after_comma(interpreter):
    out = interpreter.ev("Afstem(MnO4^- + Fe^2+ -> Mn^2+ + Fe^3+, syre)")
    assert out[0] == "MnO4^- + 5Fe^2+ + 8H3O^+ -> 12H2O + Mn^2+ + 5Fe^3+"


@pytest.mark.parametrize("line", [
    "Afstem(a,b,c)",
    "Afstem(,syre)",
    "Afstem(H2+O2->H2O,)",
])
def test_afstem_bad_input(interpreter, line):
    out = interpreter.ev(line)
    assert out[0] == "Error: " + interpreter.help_text["Afstem"]


@pytest.mark.parametrize("line, message", [
    ("Afstem(H2+O2->Xx)", "Error: Xx is not a valid atom"),
    ("Afstem(H2->O2)", "Error: Reaction cannot be balanced uniquely"),
])
def test_afstem_chemistry_errors(interpreter, line, message):
    assert interpreter.ev(line)[0] == message


# --- pH and pOH ---

@pytest.mark.parametrize("line, expected", [
    ("pH(4.76,0.10)", "2.88"),
    ("pH(4.76, 0.10)", "2.88"),
    ("pH(ethansyre,0.10)", "2.88"),
    ("pH(4.76,0.100)", "2.883"),       # rounded to the significant figures of the concentration
    ("pH(4.76,0.1)", "2.9"),
    ("  pH(4.76,0.10)  ", "2.88"),
    ("pOH(4.75,0.10)", "2.88"),
])
def test_pH_and_pOH(interpreter, line, expected):
    assert interpreter.ev(line)[0] == expected


@pytest.mark.parametrize("line", [
    "pH(4)",
    "pH(4,1,2)",
    "pH(,0.1)",
    "pH(4,)",
])
def test_pH_bad_input(interpreter, line):
    out = interpreter.ev(line)
    assert out[0] == "Error: " + interpreter.help_text["pH"]


@pytest.mark.parametrize("line", [
    "pOH(4)", 
    "pOH(4,1,2)", 
    "pOH(,0.1)"
])
def test_pOH_bad_input(interpreter, line):
    out = interpreter.ev(line)
    assert out[0] == "Error: " + interpreter.help_text["pOH"]


def test_pH_unknown_acid(interpreter):
    assert interpreter.ev("pH(findesikke,0.1)")[0] == 'Error: ukendt syre "findesikke"'


def test_pOH_unknown_base(interpreter):
    assert interpreter.ev("pOH(findesikke,0.1)")[0] == 'Error: ukendt base "findesikke"'


def test_pH_zero_concentration(interpreter):
    assert interpreter.ev("pH(4.76,0)")[0].startswith("Error")



@pytest.mark.parametrize("line,expected",[
    ("EnhedKonvertering(4[km],SI)","4000 m"),
    ("EnhedKonvertering(4[l],dl)","40 dl"),
    ("EnhedKonvertering(4[mol],SI)","4 mol")

])

def test_EnhedKonvertering(interpreter,line,expected):
    assert str(interpreter.ev(line)[0]) == expected

@pytest.mark.parametrize("line",[
    "EnhedKonvertering()",
    "EnhedKonvertering(4[mol],)",
    "EnhedKonvertering(,mol)",
    "EnhedKonvertering(4[mol],SI,1)",
    
])

def test_EnhedKonvertering_bad_input(interpreter,line):
    assert interpreter.ev(line)[0] == 'Error: EnhedKonvertering(Quantity,ny Enhed eller "SI" for SI enhed)'



def test_loop_over_its_own_line_is_an_error(interpreter):
    out = interpreter.ev("1+1\nLoop(1,2,2)")
    assert str(out[0]) == "2.0"
    assert out[1] == "Error: " + interpreter.help_text["Loop"]


def test_loop_with_non_number_does_not_stop_other_lines(interpreter):
    out = interpreter.ev("1+1\nLoop(a,1,2)\n2+2")
    assert str(out[0]) == "2.0"
    assert out[1].startswith("Error")
    assert str(out[2]) == "4.0"


def test_each_line_gets_its_own_result(interpreter):
    out = interpreter.ev("pH(4.76,0.10)\nHelp(pH)\n1+1")
    assert out[0] == "2.88"
    assert out[1] == interpreter.help_text["pH"]
    assert str(out[2]) == "2.0"
