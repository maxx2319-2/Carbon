# The old line-based interpreter. Every Kemi/Fysik/Biotek panel in the GUI builds one of these commands.
import pytest
import chem
import interpreter
from quantity import quantity as Q

HEALTHY = "ATGGCCATTGTAATGGGCCGCTGAAAGGGTGCCCGA"


def run(text):
    return interpreter.EV().ev(text)


def result(line):
    return run(line)[0]


# --- general ---

def test_help_lists_every_function():
    assert result("help").splitlines() == interpreter.EV().functions


@pytest.mark.parametrize("name", interpreter.EV().functions)
def test_every_listed_function_is_handled(name):
    # with no arguments every command fails, but it must not be "ukendt function"
    assert "ukendt function" not in str(run(name).get(0, ""))


def test_unknown_command():
    assert "ukendt function" in result("ukendt 1")


@pytest.mark.parametrize("text", ["# kommentar", "#"])
def test_comment_gives_no_output(text):
    assert run(text) == {}


def test_output_is_keyed_by_line_number():
    out = run("\n\nDNA_til_peptid ATG")
    assert out == {2: "Met, "}


def test_error_does_not_stop_next_line():
    out = run("ukendt\nDNA_til_peptid ATG")
    assert out[0].startswith("Error")
    assert out[1] == "Met, "


# --- chemistry ---

@pytest.mark.parametrize("line, expected", [
    ("balance_reaction None H2+O2->H2O", "2H2 + O2 -> 2H2O"),
    ("balance_reaction syre MnO4^- + Fe^2+ -> Mn^2+ + Fe^3+",
     "MnO4^- + 5Fe^2+ + 8H3O^+ -> 12H2O + Mn^2+ + 5Fe^3+"),
])
def test_balance_reaction(line, expected):
    assert result(line) == expected


def test_balance_reaction_error():
    assert result("balance_reaction None H2+O2").startswith("Error")


@pytest.mark.parametrize("line, expected", [
    ("pH 4.76 0.10", 2.9),          # rounded to the significant figures of the concentration
    ("pH 4.76 0.100", 2.88),
    ("pH ethansyre 0.10", 2.9),
    ("pOH 4.75 0.10", 2.9),
])
def test_pH(line, expected):
    assert result(line) == expected


def test_pH_converts_concentration_units():
    assert result("pH 4.76 100[mmol/l]") == result("pH 4.76 0.100")


def test_pH_unknown_acid():
    assert result("pH findesikke 0.1") == 'Error: ukendt syre "findesikke"'


def test_analysis():
    assert result("analysis C6H12O6") == (
        "Molekyle: C6H12O6\n Empirisk formel: CH2O\n Molar masse: 180.16\n DBE: 1.0 \n"
        " Antal atomer: 24 \n Procent indehold:\nC: 25.0%\nH: 50.0%\nO: 25.0%"
    )


# whole first, then part: that's the order the GUI panels send them in
@pytest.mark.parametrize("line, expected", [
    ("udbytteprocent 10 8", "80%"),
    ("masseprocent 8.0[g] 2.0[g]", "25%"),
    ("volumenprocent 1.00[l] 250[ml]", "25.0%"),
])
def test_percent(line, expected):
    assert result(line) == expected


@pytest.mark.parametrize("line, expected", [
    ("mængdeberegning n=2.0 M=18.0", "Masse: 36 g\nStofmængde: 2 mol\nMolarmasse: 18 g/mol"),
    ("mængdeberegning m=36[g] M=18[g/mol]", "Masse: 36 g\nStofmængde: 2.0 mol\nMolarmasse: 18 g/mol"),
    ("mængdeberegning c=0.5 V=2", "Volumen: 2 l\nStofmængde: 1 mol\nKoncentration: 0.5 mol/l"),
    ("mængdeberegning m=2.5[kg] M=18", "Masse: 2500 g\nStofmængde: 140 mol\nMolarmasse: 18 g/mol"),
])
def test_mængdeberegning(line, expected):
    assert result(line) == expected


def test_mængdeberegning_unknown_input():
    assert result("mængdeberegning x=2") == "Error: Ukendt input 'x'"


def test_puffer():
    assert result("puffer 0.10 1.0 4.76") == 5.8


def test_puffer_converts_units():
    assert result("puffer 100[mmol/l] 1.0 4.76") == result("puffer 0.100 1.0 4.76")


def test_pH_to_concentration():
    assert result("pH_to_concentration 3") == "[H3O+]: 1.000000e-03 mol/l \n [OH-]: 1.000000e-11 mol/l"


def test_pOH_to_concentration():
    assert result("pOH_to_concentration 3") == "[OH-]: 1.000000e-03 mol/l \n [H3O+]: 1.000000e-11 mol/l"


def test_empirisk_analyse():
    assert result("empirisk_analyse Fe 69.9 O 30.1") == "Fe2O3"


def test_bjerrumdiagram(monkeypatch):
    drawn = []
    monkeypatch.setattr(chem, "bjerrum", drawn.append)
    assert run("bjerrumdiagram 2.12,7.21,12.67") == {}
    assert drawn == [[2.12, 7.21, 12.67]]


# --- units ---

@pytest.mark.parametrize("line, expected", [
    ("SI 5[km]", Q(5000, {"m": 1})),
    ("SI 36[km/timer]", Q(10, {"m": 1, "s": -1})),
    ("unit_convert 5[km] m", Q(5000, {"m": 1})),
    ("unit_convert 36[km/timer] m/s", Q(10, {"m": 1, "s": -1})),
    ("unit_convert 1[m^3] l", Q(1000, {"l": 1})),
])
def test_unit_commands(line, expected):
    out = result(line)
    assert out.value == pytest.approx(expected.value)
    assert out.units == expected.units


@pytest.mark.parametrize("line, message", [
    ("SI 5[foo]", "Error: Ukendt enhed: foo"),
    ("unit_convert 5,0[km] m", "Error: Brug punktum"),
    ("unit_convert 5km m", "Error: could not parse value/unit"),
    ("unit_convert 1[m] s", "Error: cannot convert"),
])
def test_unit_command_errors(line, message):
    assert result(line).startswith(message)


# --- biology ---

def test_DNA_til_peptid():
    assert result("DNA_til_peptid ATG AAA") == "Met, Lys, "


def test_RNA_til_peptid():
    assert result("RNA_til_peptid AUGUUU") == "Met, Phe, "


def test_mutations_analyse_DNA():
    mutated = HEALTHY[:6] + "C" + HEALTHY[7:]
    assert result(f"mutations_analyse_DNA {HEALTHY}, {mutated}") == "mutationer:\nMissense mutation ved base nr 7"


def test_mutations_analyse_RNA():
    assert result("mutations_analyse_RNA AUGGCC, AUGGCC") == "mutationer:\nIngen mutation begge strenge er det samme"


def test_mutations_analyse_needs_two_strands():
    assert result("mutations_analyse_DNA ATG").startswith("Error")


# --- helpers ---

def with_variable(name, value):
    e = interpreter.EV()
    e.variables[name] = interpreter.Variables(value, "float")
    e._invalidate_pattern()
    return e


def test_prep_ev_turns_unit_brackets_into_parentheses():
    assert interpreter.EV().prep_ev("2[m]*3[mol/l]") == "2 (m)*3 (mol/l)"


def test_prep_ev_replaces_variables_outside_brackets_only():
    assert with_variable("m", "5").prep_ev("m*2[m]") == "5*2 (m)"


def test_prep_ev_replaces_whole_names_only():
    assert with_variable("x", "5").prep_ev("xx+x") == "xx+5"


@pytest.mark.parametrize("text, expected", [
    ("5[km]", (5.0, "km")),
    ("2.5[m/s]", (2.5, "m/s")),
    (" 3 [g]", (3.0, "g")),
])
def test_unit_bracket_strip(text, expected):
    assert interpreter.EV().unit_bracket_strip(text) == expected


@pytest.mark.parametrize("text, message", [
    ("5km", "could not parse"),
    ("[km]", "could not parse"),
    ("5,0[km]", "punktum"),
])
def test_unit_bracket_strip_errors(text, message):
    with pytest.raises(ValueError, match=message):
        interpreter.EV().unit_bracket_strip(text)


def test_as_expr():
    assert interpreter.as_expr(Q(2.0, {"m": 1, "s": -2})) == "(2.0*m^(1)*s^(-2))"
