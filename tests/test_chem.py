import re

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pytest
import chem


def test_periodic_table_is_complete():
    assert len(chem.atoms) == len(set(chem.atoms)) == 118


# --- reaction parsing ---

@pytest.mark.parametrize("formula, expected", [
    ("Fe^3+", ("Fe", 3)),
    ("Na^+", ("Na", 1)),
    ("OH^-", ("OH", -1)),
    ("SO4^2-", ("SO4", -2)),
    ("H2O", ("H2O", 0)),
])
def test_split_charge(formula, expected):
    assert chem.split_charge(formula) == expected


def test_reaction_parser():
    assert chem.reaction_parser("H2 + O2 -> H2O") == (
        [("H", 2, 1), ("O", 2, 2)],
        [("H", 2, 3), ("O", 1, 3)],
    )


def test_reaction_parser_keeps_charges():
    reactants, _ = chem.reaction_parser("Fe^3+ + OH^- -> FeO3H3")
    assert ("charge", 3, 1) in reactants
    assert ("charge", -1, 2) in reactants


def test_reaction_parser_unknown_atom():
    with pytest.raises(ValueError, match="Xx is not a valid atom"):
        chem.reaction_parser("Xx + O2 -> XxO")


def test_build_matrix():
    matrix, elements = chem.build_matrix(*chem.reaction_parser("H2+O2->H2O"))
    assert elements == ["H", "O"]
    assert matrix.tolist() == [[2, 0, -2], [0, 2, -1]]


def test_get_coefficients():
    matrix, _ = chem.build_matrix(*chem.reaction_parser("H2+O2->H2O"))
    assert chem.get_coefficients(matrix) == [2, 1, 2]


def test_get_coefficients_not_unique():
    with pytest.raises(ValueError, match="cannot be balanced uniquely"):
        chem.get_coefficients(np.array([[1.0, -1.0, 0, 0], [0, 0, 1.0, -1.0]]))


# --- balancing ---

def count_side(side):
    # atoms and total charge on one side of a balanced reaction, e.g. "2H2 + O2"
    total = {"charge": 0}
    for term in side.split(" + "):
        coef, formula = re.fullmatch(r"(\d*)(.+)", term.strip()).groups()
        coef = int(coef) if coef else 1
        body, charge = chem.split_charge(formula)
        for atom, n in re.findall(r"([A-Z][a-z]?)(\d*)", body):
            total[atom] = total.get(atom, 0) + coef * (int(n) if n else 1)
        total["charge"] += coef * charge
    return total


REACTIONS = [
    ("H2+O2->H2O", None),
    ("CH4+O2->CO2+H2O", None),
    ("C3H8+O2->CO2+H2O", None),
    ("C6H12O6+O2->CO2+H2O", None),
    ("Fe+O2->Fe2O3", None),
    ("KClO3->KCl+O2", None),
    ("Cu + Ag^+ -> Cu^2+ + Ag", None),
    ("MnO4^- + Fe^2+ -> Mn^2+ + Fe^3+", "syre"),
    ("Cr2O7^2- + Fe^2+ -> Cr^3+ + Fe^3+", "syre"),
    ("MnO4^- + I^- -> MnO2 + I2", "base"),
]


@pytest.mark.parametrize("reaction, medium", REACTIONS)
def test_balanced_reaction_conserves_atoms_and_charge(reaction, medium):
    left, right = chem.balance_reaction(reaction, medium).split(" -> ")
    assert count_side(left) == count_side(right)


@pytest.mark.parametrize("reaction, expected", [
    ("H2+O2->H2O", "2H2 + O2 -> 2H2O"),
    ("H2 + O2 -> H2O", "2H2 + O2 -> 2H2O"),
    ("H2O->H2+O2", "2H2O -> 2H2 + O2"),
    ("CH4+O2->CO2+H2O", "CH4 + 2O2 -> CO2 + 2H2O"),
    ("C3H8+O2->CO2+H2O", "C3H8 + 5O2 -> 3CO2 + 4H2O"),
    ("C6H12O6+O2->CO2+H2O", "C6H12O6 + 6O2 -> 6CO2 + 6H2O"),
    ("C2H5OH+O2->CO2+H2O", "C2H5OH + 3O2 -> 2CO2 + 3H2O"),
    ("Fe+O2->Fe2O3", "4Fe + 3O2 -> 2Fe2O3"),
    ("N2+H2->NH3", "N2 + 3H2 -> 2NH3"),
    ("KClO3->KCl+O2", "2KClO3 -> 2KCl + 3O2"),
    ("NaOH+HCl->NaCl+H2O", "NaOH + HCl -> NaCl + H2O"),
    ("H2O->H2O", "H2O -> H2O"),
])
def test_balance_reaction(reaction, expected):
    assert chem.balance_reaction(reaction) == expected


@pytest.mark.parametrize("reaction, expected", [
    ("Ag^+ + Cl^- -> AgCl", "Ag^+ + Cl^- -> AgCl"),
    ("Cu + Ag^+ -> Cu^2+ + Ag", "Cu + 2Ag^+ -> Cu^2+ + 2Ag"),
    ("Fe^3+ + OH^- -> FeO3H3", "Fe^3+ + 3OH^- -> FeO3H3"),
])
def test_balance_ions(reaction, expected):
    assert chem.balance_reaction(reaction) == expected


@pytest.mark.parametrize("reaction, medium, expected", [
    ("MnO4^- + Fe^2+ -> Mn^2+ + Fe^3+", "syre",
     "MnO4^- + 5Fe^2+ + 8H3O^+ -> 12H2O + Mn^2+ + 5Fe^3+"),
    ("MnO4^- + Fe^2+ -> Mn^2+ + Fe^3+", "SYRE",
     "MnO4^- + 5Fe^2+ + 8H3O^+ -> 12H2O + Mn^2+ + 5Fe^3+"),
    ("Cr2O7^2- + Fe^2+ -> Cr^3+ + Fe^3+", "syre",
     "Cr2O7^2- + 6Fe^2+ + 14H3O^+ -> 21H2O + 2Cr^3+ + 6Fe^3+"),
    ("MnO4^- + I^- -> MnO2 + I2", "base",
     "2MnO4^- + 6I^- + 4H2O -> 8OH^- + 2MnO2 + 3I2"),
    ("H2+O2->H2O", "base", "2H2 + O2 -> 2H2O"),    # OH^- isn't needed, so it gets 0 and is left out
])
def test_balance_redox(reaction, medium, expected):
    assert chem.balance_reaction(reaction, medium) == expected


@pytest.mark.parametrize("reaction", ["H2+O2", "h2+o2->h2o"])
def test_balance_reaction_bad_input(reaction):
    with pytest.raises(ValueError):
        chem.balance_reaction(reaction)


def test_balance_reaction_unknown_atom():
    with pytest.raises(ValueError, match="Xx is not a valid atom"):
        chem.balance_reaction("H2+O2->Xx")


def test_balance_reaction_impossible():
    with pytest.raises(ValueError, match="cannot be balanced uniquely"):
        chem.balance_reaction("H2->O2")


@pytest.mark.xfail(reason="atoms inside parentheses are counted once and the number after ) is ignored")
def test_balance_with_parentheses():
    assert chem.balance_reaction("Ca(OH)2+HCl->CaCl2+H2O") == "Ca(OH)2 + 2HCl -> CaCl2 + 2H2O"


@pytest.mark.xfail(reason="a coefficient the user typed is glued onto the new one: 2H2 becomes 22H2")
def test_balance_ignores_typed_coefficients():
    assert chem.balance_reaction("2H2+O2->H2O") == "2H2 + O2 -> 2H2O"


# --- pH and pOH ---

@pytest.mark.parametrize("acid, c, expected", [
    ("4.76", "0.1", 2.883),         # weak acid
    ("ethansyre", "0.1", 2.883),    # looked up in pKa_values
    ("4.76", "1e-3", 3.909),
    ("9.25", "0.1", 5.125),
    ("0", "1", 0.209),
    ("saltsyre", "0.1", 1.000),     # strong acid: pH = -log(c)
    ("saltsyre", "0.01", 2.000),
    ("hydrogeniodid", "0.1", 1.000),
    ("-7", "0.1", 1.000),
])
def test_pH(acid, c, expected):
    assert chem.pH(acid, c) == pytest.approx(expected, abs=0.001)


@pytest.mark.parametrize("name", list(chem.pKa_values))
def test_every_named_acid_gives_a_sensible_pH(name):
    # 0.1 M of any acid: not more acidic than a strong acid, and still acidic
    assert 0.99 < chem.pH(name, "0.1") < 7


def test_pH_unknown_acid():
    with pytest.raises(ValueError, match='ukendt syre "findesikke"'):
        chem.pH("findesikke", "0.1")


@pytest.mark.parametrize("c", ["0", "-1"])
def test_pH_needs_positive_concentration(c):
    with pytest.raises(ValueError):
        chem.pH("4.76", c)


def test_pOH():
    assert chem.pOH("4.75", "0.1") == pytest.approx(2.878, abs=0.001)


def test_pOH_uses_same_formula_as_pH():
    assert chem.pOH("4.76", "0.1") == chem.pH("4.76", "0.1")


def test_pOH_unknown_base():
    with pytest.raises(ValueError, match='ukendt base "findesikke"'):
        chem.pOH("findesikke", "0.1")


@pytest.mark.parametrize("pH, h3o, oh", [
    (3, 1e-3, 1e-11),
    (7, 1e-7, 1e-7),
    (0, 1, 1e-14),
    (14, 1e-14, 1),
    (2.5, 3.162e-3, 3.162e-12),
])
def test_pH_to_concentration(pH, h3o, oh):
    assert chem.pH_to_concentration(pH) == pytest.approx((h3o, oh), rel=1e-3)


@pytest.mark.parametrize("syre, base, expected", [
    (1, 1, 4.76),       # equal amounts: pH = pKs
    (0.1, 1, 5.76),
    (1, 0.1, 3.76),
])
def test_puffer(syre, base, expected):
    assert chem.puffer(syre, base, 4.76) == pytest.approx(expected)


@pytest.mark.parametrize("syre, base", [(0, 1), (1, 0)])
def test_puffer_needs_both_acid_and_base(syre, base):
    with pytest.raises((ZeroDivisionError, ValueError)):
        chem.puffer(syre, base, 4.76)


# --- formulas and analysis ---

@pytest.mark.parametrize("formula, expected", [
    ("CH3CH2OH", "C2H6O"),      # same atoms are added up, in the order they first appear
    ("CH3COOH", "C2H4O2"),
    ("HHO", "H2O"),
    ("H2O", "H2O"),
    ("NaCl", "NaCl"),
    ("He", "He"),
    ("", ""),
])
def test_molecule_formula(formula, expected):
    assert chem.molecule_formula(formula) == expected


@pytest.mark.xfail(reason="parentheses are ignored, so the 2 after (OH) is lost")
def test_molecule_formula_with_parentheses():
    assert chem.molecule_formula("Ca(OH)2") == "CaO2H2"


def test_elemental_analysis_glucose():
    molecule, empirical, molar_mass, atom_count, procent, dbe = chem.elemental_analasis("C6H12O6")
    assert molecule == "C6H12O6"
    assert empirical == "CH2O"
    assert molar_mass == pytest.approx(180.156, abs=0.01)
    assert atom_count == 24
    assert procent == ["C: 25.0%", "H: 50.0%", "O: 25.0%"]
    assert dbe == 1


@pytest.mark.parametrize("formula, empirical", [
    ("H2O", "H2O"),
    ("C6H6", "CH"),
    ("O2", "O"),
    ("CH3CH2OH", "C2H6O"),
    ("CH3NH2", "CH5N"),
])
def test_empirical_formula(formula, empirical):
    assert chem.elemental_analasis(formula)[1] == empirical


@pytest.mark.parametrize("formula, molar_mass", [
    ("H2O", 18.015),
    ("CO2", 44.009),
    ("NaCl", 58.44),
    ("C6H12O6", 180.156),
])
def test_molar_mass(formula, molar_mass):
    assert chem.elemental_analasis(formula)[2] == pytest.approx(molar_mass, abs=0.01)


@pytest.mark.parametrize("formula, dbe", [
    ("CH4", 0),
    ("C2H4", 1),
    ("C2H2", 2),
    ("C6H6", 4),
    ("C2H5Cl", 0),      # halogens count like H
    ("C6H5Br", 4),
    ("CH3NH2", 0),
    ("C5H5N", 4),
])
def test_double_bond_equivalents(formula, dbe):
    assert chem.elemental_analasis(formula)[5] == dbe


@pytest.mark.parametrize("formula", ["H2O", "CH3CH2OH", "C2H5Cl", "CH3NH2"])
def test_atom_percentages_add_up_to_100(formula):
    procent = chem.elemental_analasis(formula)[4]
    assert sum(float(p.split(": ")[1].rstrip("%")) for p in procent) == pytest.approx(100, abs=0.05)


@pytest.mark.parametrize("text, expected", [
    ("Fe 69.9 O 30.1", "Fe2O3"),
    ("K 26.6 Cr 35.4 O 38.0", "K2Cr2O7"),
])
def test_empirical_analysis(text, expected):
    assert chem.emperical_analysis(text) == expected


def test_empirical_analysis_input_formats():
    assert (chem.emperical_analysis("C 40 H 6.7 O 53.3")
            == chem.emperical_analysis("C40H6.7O53.3")
            == chem.emperical_analysis("C 40,0 H 6,7 O 53,3"))


@pytest.mark.xfail(reason="a count of 1 is written out (C1H2O1), unlike everywhere else in the app")
@pytest.mark.parametrize("text, expected", [
    ("C 40 H 6.7 O 53.3", "CH2O"),
    ("Na 39.3 Cl 60.7", "NaCl"),
    ("C 85.6 H 14.4", "CH2"),
])
def test_empirical_analysis_leaves_out_ones(text, expected):
    assert chem.emperical_analysis(text) == expected


@pytest.mark.parametrize("nums, expected", [
    ([1, 0.5], [2, 1]),
    ([1, 1.5], [2, 3]),
    ([1, 1.333], [3, 4]),
    ([1, 0.333333], [3, 1]),
    ([1, 2.5, 0.75], [4, 10, 3]),
    ([1, 2, 3], [1, 2, 3]),
])
def test_to_whole(nums, expected):
    assert chem.to_whole(nums) == expected


# --- percent and amounts ---

@pytest.mark.parametrize("whole, part, expected", [
    (50, 25, 50.0),
    (4, 1, 25.0),
    (10, 12, 120.0),
])
def test_procent(whole, part, expected):
    assert chem.procent(whole, part) == expected


def test_procent_of_zero():
    with pytest.raises(ZeroDivisionError):
        chem.procent(0, 1)


@pytest.mark.parametrize("given, key, expected", [
    ({"Stofmængde": 2, "Molarmasse": 18}, "Masse", 36),         # m = n*M
    ({"Masse": 36, "Molarmasse": 18}, "Stofmængde", 2),          # n = m/M
    ({"Masse": 36, "Stofmængde": 2}, "Molarmasse", 18),          # M = m/n
    ({"Densitet": 1.5, "Volumen": 2}, "Masse", 3),               # m = p*V
    ({"Masse": 3, "Densitet": 1.5}, "Volumen", 2),               # V = m/p
    ({"Masse": 2, "Volumen": 4}, "Densitet", 0.5),               # p = m/V
    ({"Koncentration": 0.5, "Volumen": 2}, "Stofmængde", 1),     # n = c*V
    ({"Stofmængde": 1, "Koncentration": 0.5}, "Volumen", 2),     # V = n/c
    ({"Stofmængde": 1, "Volumen": 4}, "Koncentration", 0.25),    # c = n/V
])
def test_mængdeberegning(given, key, expected):
    assert chem.mængdeberegning(**given)[key] == pytest.approx(expected)


def test_mængdeberegning_chains_formulas():
    # c and V give n, then n and M give m
    result = chem.mængdeberegning(Koncentration=0.5, Volumen=2, Molarmasse=18)
    assert result["Stofmængde"] == pytest.approx(1)
    assert result["Masse"] == pytest.approx(18)


def test_mængdeberegning_chains_backwards():
    # m and M give n, then n and c give V
    result = chem.mængdeberegning(Masse=36, Molarmasse=18, Koncentration=0.5)
    assert result["Stofmængde"] == pytest.approx(2)
    assert result["Volumen"] == pytest.approx(4)


def test_mængdeberegning_keeps_given_values():
    result = chem.mængdeberegning(Masse=10, Stofmængde=1, Molarmasse=99)
    assert (result["Masse"], result["Stofmængde"], result["Molarmasse"]) == (10, 1, 99)


def test_mængdeberegning_with_too_little_given():
    assert chem.mængdeberegning(Masse=5) == {
        "Masse": 5, "Volumen": None, "Stofmængde": None,
        "Koncentration": None, "Molarmasse": None, "Densitet": None,
    }


# --- Bjerrum diagrams ---

def test_bjerrum_figure():
    ax = chem.bjerrum_figure([4.76, 9.25]).axes[0]
    curves = [line.get_label() for line in ax.lines if line.get_label().startswith("pKs")]
    assert curves == ["pKs: 4.76", "pKs: 9.25"]
    assert ax.get_xlim() == (0, 14)
    assert ax.get_ylim() == (0, 1)


@pytest.mark.parametrize("pks", [2.0, 4.76, 12.5])
def test_bjerrum_curve(pks):
    x, y = chem.bjerrum_figure([pks]).axes[0].lines[0].get_data()
    assert np.interp(pks, x, y) == pytest.approx(0.5, abs=0.01)    # half acid, half base at pH = pKs
    assert np.all(np.diff(y) < 0)                                   # less acid the higher the pH


def test_bjerrum_window(monkeypatch):
    monkeypatch.setattr(plt, "show", lambda: None)
    with matplotlib.rc_context():       # bjerrum() changes the global plot style
        chem.bjerrum([4.76])
        labels = [line.get_label() for line in plt.gca().lines]
    plt.close("all")
    assert "pKs: 4.76" in labels
