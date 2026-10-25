import re
import numpy as np
from scipy.linalg import null_space
from fractions import Fraction
from math import gcd
import math
import json
from types import SimpleNamespace
from mendeleev import element
import matplotlib.pyplot as plt
from cycler import cycler
from path import resource_path
from math import lcm
import parser
from quantity import quantity

with open(resource_path("config.json")) as f:
    config = json.load(f, object_hook=lambda d: SimpleNamespace(**d))


CHAIN_STEM = ["meth", "eth", "prop", "but", "pent", "hex", "hept", "oct", "non", "dec"]
UNSAT_INFIX = ["an", "en", "yn"]
SUFFIX = ["ol", "one", "al", "oic acid", "amine", "nitrile", "amide", "oate"]
MULTIPLYERS = [
    "tetrakis",
    "pentakis",
    "tetra",
    "penta",
    "hexa",
    "hepta",
    "octa",
    "nona",
    "deca",
    "tris",
    "bis",
    "di",
    "tri",
]
SUBSTITUENT = [
    "hydroxy",
    "amino",
    "methoxy",
    "ethoxy",
    "chloro",
    "bromo",
    "fluoro",
    "iodo",
    "methyl",
    "ethyl",
    "propyl",
    "butyl",
    "oxo",
    "cyano",
    "nitro",
]


MULTIPLYERS_DICT = {
    "di": 2,
    "bis": 2,
    "tri": 3,
    "tris": 3,
    "tetra": 4,
    "tetrakis": 4,
    "penta": 5,
    "pentakis": 5,
    "hexa": 6,
    "hepta": 7,
    "octa": 8,
    "nona": 9,
    "deca": 10,
}

atoms = [
    # Period 1
    "H",
    "He",
    # Period 2
    "Li",
    "Be",
    "B",
    "C",
    "N",
    "O",
    "F",
    "Ne",
    # Period 3
    "Na",
    "Mg",
    "Al",
    "Si",
    "P",
    "S",
    "Cl",
    "Ar",
    # Period 4
    "K",
    "Ca",
    "Sc",
    "Ti",
    "V",
    "Cr",
    "Mn",
    "Fe",
    "Co",
    "Ni",
    "Cu",
    "Zn",
    "Ga",
    "Ge",
    "As",
    "Se",
    "Br",
    "Kr",
    # Period 5
    "Rb",
    "Sr",
    "Y",
    "Zr",
    "Nb",
    "Mo",
    "Tc",
    "Ru",
    "Rh",
    "Pd",
    "Ag",
    "Cd",
    "In",
    "Sn",
    "Sb",
    "Te",
    "I",
    "Xe",
    # Period 6
    "Cs",
    "Ba",
    # Lanthanides
    "La",
    "Ce",
    "Pr",
    "Nd",
    "Pm",
    "Sm",
    "Eu",
    "Gd",
    "Tb",
    "Dy",
    "Ho",
    "Er",
    "Tm",
    "Yb",
    "Lu",
    "Hf",
    "Ta",
    "W",
    "Re",
    "Os",
    "Ir",
    "Pt",
    "Au",
    "Hg",
    "Tl",
    "Pb",
    "Bi",
    "Po",
    "At",
    "Rn",
    # Period 7
    "Fr",
    "Ra",
    # Actinides
    "Ac",
    "Th",
    "Pa",
    "U",
    "Np",
    "Pu",
    "Am",
    "Cm",
    "Bk",
    "Cf",
    "Es",
    "Fm",
    "Md",
    "No",
    "Lr",
    "Rf",
    "Db",
    "Sg",
    "Bh",
    "Hs",
    "Mt",
    "Ds",
    "Rg",
    "Cn",
    "Nh",
    "Fl",
    "Mc",
    "Lv",
    "Ts",
    "Og",
]


pKa_values = {
    "svolsyre": -3,
    "Salpetersyre": -1.35,
    "saltsyre": -7,
    "hydrogeniodid": -9.5,
    "hydrogenbromid": -8,
    "svovlsyre": -3,
    "bromsyre": -1,
    "oxonium": 0,
    "chlorsyre": -1.58,
    "iodsyre": 0.82,
    "phosphorsyre": 2.12,
    "flussyre": 2.17,
    "ethansyre": 4.76,
    "carbonsyre": 6.37,
    "borsyre": 9.24,
    "ammonium": 9.25,
}

pKb_values = {

}

def split_charge(formula):
    m = re.match(r'^(.*?)\^(\d*)([+-])$', formula)
    if not m:
        return formula, 0
    body,num,sign = m.groups()
    n = int(num) if num else 1
    return body,n if sign == "+" else -n




def reaction_parser(reaction):

    reaction = reaction.replace(" ", "")
    reactant, product = reaction.split("->")


    reactants = []
    products = []
    compund = 0
    for side, out in ((reactant, reactants), (product, products)):
        for formula in re.findall(r"[A-Za-z0-9()]+(?:\^\d*[+-])?", side):
            compund +=1
            body,charge = split_charge(formula)
            for part, amount in re.findall(r"([A-Z][a-z]?)(\d*)", body):
                if part not in atoms:
                    raise ValueError(f"{part} is not a valid atom")
                out.append((part,int(amount) if amount else 1, compund))
            if charge:
                out.append(("charge",charge,compund))




    return reactants,products



def build_matrix(reactants, products):

    all_entries = reactants + products
    elements = sorted(set(entry[0] for entry in all_entries)) 

    num_compounds = max(entry[2] for entry in all_entries)

    elem_index = {elem: i for i, elem in enumerate(elements)}

    matrix = np.zeros((len(elements), num_compounds))

    for element, count, compound_id in reactants:
        row = elem_index[element]
        col = compound_id - 1
        matrix[row][col] += count

    for element, count, compound_id in products:
        row = elem_index[element]
        col = compound_id - 1
        matrix[row][col] -= count

    return matrix, elements


def get_coefficients(matrix):
    ns = null_space(matrix)
    if ns.shape[1] != 1:
        raise ValueError("Reaction cannot be balanced uniquely")

    vec = ns[:, 0]
    vec = vec / np.min(abs(vec[np.abs(vec) > 1e-8]))

    fracs = [Fraction(x).limit_denominator(100) for x in vec]
    lcm = 1
    for f in fracs:
        lcm = lcm * f.denominator // gcd(lcm, f.denominator)
    coeffs = [int(round(f * lcm)) for f in fracs]
    if coeffs[0] < 0:
        coeffs = [-c for c in coeffs]
    return coeffs


def balance_reaction(reaction, medium=None):
    if "<->" in reaction:
        arrow = "equlibrium"
    elif "->" in reaction:
        arrow = "one way"
    else: raise ValueError("Ukendt eller ingen reaktionpil")

    reactant_side, product_side = re.split(r"<?->",reaction.replace(" ", ""))
    reactant = re.findall(r"[A-Za-z0-9()]+(?:\^\d*[+-])?", reactant_side)
    product = re.findall(r"[A-Za-z0-9()]+(?:\^\d*[+-])?", product_side)
    if medium:
        medium = medium.lower()

    if medium == "syre":
        helpers = ["H3O^+", "H2O"]
    elif medium == "base":
        helpers = ["OH^-", "H2O"]
    else:
        helpers = []
    reactant += [h for h in helpers if h not in reactant + product]

    reactants, products = reaction_parser("+".join(reactant) + "->" + "+".join(product))
    matrix, elements = build_matrix(reactants, products)
    co = get_coefficients(matrix)

    left = []
    right = []
    for i, (c, formula) in enumerate(zip(co, reactant + product)):
        if i >= len(reactant):
            c = -c
        if c > 0:
            left.append(formula if c == 1 else f"{c}{formula}")
        elif c < 0:
            right.append(formula if c == -1 else f"{-c}{formula}")
    if arrow == "equlibrium":
        return " + ".join(left) + " <-> " + " + ".join(right)
    return " + ".join(left) + " -> " + " + ".join(right)
    






def pH(x, con):
    if x[0].isalpha():
        if x not in pKa_values:
            raise ValueError(f'ukendt syre "{x}"')
        k = 10 ** -float(pKa_values[x])
    else:
        k = 10 ** -float(x)

    H3O = (2*con)/(1+math.sqrt(1+((4*con)/k)))
    ph = -math.log10(H3O)

    return ph


def pOH(x, con):
    if x[0].isalpha():
        if x not in pKb_values:
                    raise ValueError(f'ukendt base "{x}"')
        k = 10 ** -float(pKb_values[x])
    else:
        k = 10 ** -float(x)

    OH = (2*con)/(1+math.sqrt(1+((4*con)/k)))
    poh = -math.log10(OH)

    return poh


def molecule_formula(x):
    molecule_dict = {}
    matches = re.findall(r"([A-Z][a-z]?)(\d*)", x)
    matches = [(atom, amount) for atom, amount in matches if atom]
    parsed = [(atom, int(amount) if amount else 1) for atom, amount in matches]

    for part in parsed:
        if part[0] in molecule_dict:
            molecule_dict[part[0]] += part[1]

        else:
            molecule_dict[part[0]] = part[1]

    molecule = ""
    for part in molecule_dict:
        molecule += part
        if molecule_dict[part] != 1:
            molecule += str(molecule_dict[part])

    return molecule


def elemental_analasis(x):
    m = molecule_formula(x)

    matches = re.findall(r"([A-Z][a-z]?)(\d*)", m)
    matches = [(atom, amount) for atom, amount in matches if atom]
    parsed = [(atom, int(amount) if amount else 1) for atom, amount in matches]

    # molar mass
    molar_mass = 0
    atom_count = ()
    atom_sumcount = 0

    for atom in parsed:
        molar_mass += atom[1] * element(atom[0]).atomic_weight
        atom_count = atom_count + (atom[1],)
        atom_sumcount += atom[1]

    denominator = math.gcd(*atom_count)
    empirical = []
    empirical_formula = ""
    if denominator > 1:
        for atom in parsed:
            empirical.append([atom[0], round(atom[1] / denominator)])

    else:
        empirical_formula = m

    for part in empirical:
        empirical_formula += str(part[0])
        if part[1] != 1:
            empirical_formula += str(part[1])

    atom_procent = {}

    for part in parsed:
        atom_procent[part[0]] = round(((part[1]*element(part[0]).atomic_weight)/molar_mass)*100,config.rounding_decimals)

    procent = []
    for part in atom_procent:
        procent.append(f"{part}: {atom_procent[part]}%")

    C_count = 0
    H_count = 0
    N_count = 0
    x_count = 0
    dbe = 0

    for part in parsed:
        match part[0]:

            case "C":
                C_count += part[1]
            case "H":
                H_count += part[1]
            case "N":
                N_count += part[1]
            case "F":
                x_count += part[1]
            case "Cl":
                x_count += part[1]
            case "Br":
                x_count += part[1]
            case "I":
                x_count += part[1]

    dbe = ((2 * C_count) + 2 + N_count - H_count - x_count) / 2

    return x, empirical_formula, molar_mass, atom_sumcount, procent, dbe


def bjerrum(pks):
    plt.style.use("dark_background")
    plt.rcParams["axes.prop_cycle"] = cycler(
        color=[
            "#00d9ff",  # cyan
            "#ff6ec7",  # pink
            "#ffd166",  # yellow
            "#06ffa5",  # mint green
            "#c77dff",  # lavender/purple
            "#ff9e6d",  # coral orange
            "#7d5fff",  # violet blue
            "#ff5d8f",  # rose red
            "#5ffbf1",  # aqua
            "#ffe66d",  # pale gold
            "#b8f2e6",  # soft mint
            "#f78fb3",  # light pink
        ]
    )

    plt.rcParams.update(
        {
            "figure.facecolor": "#404040",
            "axes.facecolor": "#323232",
            "axes.edgecolor": "#555566",
            "axes.grid": True,
            "grid.color": "#1F1F28",
            "legend.facecolor": "white",
            "legend.edgecolor": "#555566",
            "legend.labelcolor": "black",
            "grid.alpha": 0.5,
            "font.size": 12,
            "axes.titlesize": 15,
            "lines.linewidth": 2.2,
            "savefig.dpi": 300,

        }
    )
    x = np.linspace(0, 14, 400)

    for acid in pks:
        y = 1 / (1 + 10 ** (x - acid))

        plt.plot(x, y, label=f"pKs: {acid}")
    plt.legend()
    plt.grid(True)
    plt.xlabel("pH")
    plt.ylabel("Syre brøk")
    plt.gcf().canvas.manager.set_window_title("Bjerrum Plot")

    plt.xlim(0, 14)
    plt.ylim(0, 1)

    plt.yticks(np.arange(0, 1.1, 0.1))
    markers = []
    for acid in pks:
        markers.append(plt.axvline(
            x=acid, color="white", linestyle=(0, (5, 4)), linewidth=2, alpha=0.5
        ))
        markers.append(plt.scatter(
            acid, 0.5, s=20, color="white", linewidth=0.5, zorder=5, clip_on=False
        ))

    fig = plt.gcf()
    ax = plt.gca()
    save = fig.savefig

    def export(*args, **kwargs):
        ax.set_facecolor("white")
        ax.tick_params(colors="black")
        ax.xaxis.label.set_color("black")
        ax.yaxis.label.set_color("black")
        for marker in markers:
            marker.set_color("black")
        try:
            save(*args, facecolor="white", **kwargs)
        finally:
            ax.set_facecolor("#323232")
            ax.tick_params(colors="white")
            ax.xaxis.label.set_color("white")
            ax.yaxis.label.set_color("white")
            for marker in markers:
                marker.set_color("white")

    fig.savefig = export

    plt.show()


def bjerrum_figure(pks):
    from matplotlib.figure import Figure

    colors = [
        "#00d9ff",
        "#ff6ec7",
        "#ffd166",
        "#06ffa5",
        "#c77dff",
        "#ff9e6d",
        "#7d5fff",
        "#ff5d8f",
        "#5ffbf1",
        "#ffe66d",
        "#b8f2e6",
        "#f78fb3",
    ]

    fig = Figure(figsize=(5, 4))
    fig.patch.set_facecolor("#404040")
    ax = fig.add_subplot(111)
    ax.set_facecolor("#323232")

    x = np.linspace(0, 14, 400)

    for i, acid in enumerate(pks):
        y = 1 / (1 + 10 ** (x - acid))
        ax.plot(
            x, y, label=f"pKs: {acid}", color=colors[i % len(colors)], linewidth=2.2
        )

    for i, acid in enumerate(pks):
        ax.axvline(x=acid, color="white", linestyle=(0, (5, 4)), linewidth=2, alpha=0.5)
        ax.scatter(
            acid, 0.5, s=20, color="white", linewidth=0.5, zorder=5, clip_on=False
        )

    legend = ax.legend(facecolor="#1e1e1e", edgecolor="#555566")
    for text in legend.get_texts():
        text.set_color("white")

    ax.grid(True, color="#1F1F28", alpha=0.5)
    ax.set_xlabel("pH", color="white")
    ax.set_ylabel("Syre brøk", color="white")
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 1)
    ax.set_yticks(np.arange(0, 1.1, 0.1))
    ax.tick_params(colors="white")
    for spine in ax.spines.values():
        spine.set_color("#555566")

    fig.tight_layout()
    return fig


def procent(top,bottom):
    if top.units != bottom.units:
        raise ValueError(f"Tæller og nævner skal have samme type enhed Tæller: {top.units} Nævner: {bottom.units}")
    
    
    result = f"({top} / {bottom}) * 100"
    result = parser.evaluate(result)
   
    return result


def mængdeberegning(
    Masse=None,
    Volumen=None,
    Stofmængde=None,
    Koncentration=None,
    Molarmasse=None,
    Densitet=None,
):
    values = {
        "Masse": Masse,
        "Volumen": Volumen,
        "Stofmængde": Stofmængde,
        "Koncentration": Koncentration,
        "Molarmasse": Molarmasse,
        "Densitet": Densitet,
    }

    changed = True
    while changed:
        changed = False

        m, V, n, c, M, p = (
            values["Masse"],
            values["Volumen"],
            values["Stofmængde"],
            values["Koncentration"],
            values["Molarmasse"],
            values["Densitet"],
        )

        if m is None and n is not None and M is not None:
            values["Masse"] = n * M
            changed = True
        elif n is None and m is not None and M is not None:
            values["Stofmængde"] = m / M
            changed = True
        elif M is None and m is not None and n is not None:
            values["Molarmasse"] = m / n
            changed = True

        if m is None and p is not None and V is not None:
            values["Masse"] = p * V
            changed = True
        elif V is None and m is not None and p is not None:
            values["Volumen"] = m / p
            changed = True
        elif p is None and m is not None and V is not None:
            values["Densitet"] = m / V
            changed = True

        if n is None and c is not None and V is not None:
            values["Stofmængde"] = c * V
            changed = True
        elif V is None and n is not None and c is not None:
            values["Volumen"] = n / c
            changed = True
        elif c is None and n is not None and V is not None:
            values["Koncentration"] = n / V
            changed = True

    return values


def puffer(syre, base, pKs):
    result = pKs + math.log10(base / syre)

    return result


def pH_to_concentration(pH):
    pOH = 14-pH
    result1 = 10**(-pH)
    result2 = 10**(-pOH)
    return result1,result2


def to_whole(nums):
    fracs = [Fraction(x).limit_denominator(10) for x in nums]
    mult = lcm(*(f.denominator for f in fracs))
    return [int(f * mult) for f in fracs]


def emperical_analysis(atom_procent):
    n = {}
    result = ""

    atom_procents = dict(re.findall(r"([A-Z][a-z]?)\s*(\d+(?:[.,]\d+)?)", atom_procent))

    for atom in atom_procents:
        M = element(atom).atomic_weight
        n[atom] = float(atom_procents[atom].replace("%", "").replace(",", ".")) / M

    divider = min(n.values())
    ratios = {atom: n[atom]/divider for atom in n}


    for factor in range(1,11):
        scaled = {atom: r* factor for atom,r in ratios.items()}
        if all(abs(v-round(v)) < 0.1 for v in scaled.values()):
            break
    for part in n:
        count = round(scaled[part])
        result += part
        if count != 0:
            result += str(count)

    return result

    





