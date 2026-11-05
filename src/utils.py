import re
import json
from types import SimpleNamespace
from decimal import Decimal
import math
import sympy
import numpy as np
from matplotlib.figure import Figure
from scipy.optimize import curve_fit


from path import resource_path

with open(resource_path("config.json")) as f:
    config = json.load(f, object_hook=lambda d: SimpleNamespace(**d))




FUNCTIONS = {
    "Ln": math.log,
    "Log": math.log10,
    "Exp": math.exp,
    "Sin": lambda x : math.sin(math.radians(x)),
    "Cos": lambda x : math.cos(math.radians(x)),
    "Tan": lambda x : math.tan(math.radians(x)),
    "ArcSin": lambda x : math.degrees(math.asin(x)),
    "ArcCos": lambda x : math.degrees(math.acos(x)),
    "ArcTan": lambda x : math.degrees(math.atan(x)),
    "Sinh": math.sinh,
    "Cosh": math.cosh,
    "Tanh": math.tanh,
    "ArcSinh": math.asinh,
    "ArcCosh": math.acosh,
    "ArcTanh": math.atanh,
    "Cbrt": math.cbrt,
    "Abs": math.fabs,
    "Floor": math.floor,
    "Ceil": math.ceil,
    "Round": lambda x, n=0: round(x, int(n)),
    "Degrees": math.degrees,
    "Radians": math.radians,
    "Gamma": math.gamma,
    "Erf": math.erf,
}


def is_positive(x):
    if x > 0 or x == 0:
        return True
    elif x < 0:
        return False


def comparison(input):
    expr = input.replace(" ", "")
    a = ""
    com = ""
    b = ""
    i = 0
    for char in expr:
        if char.isdigit() or char == ".":
            if i == 0:
                a += char

            if i == 1:
                b += char
        else:
            com += char
            if i == 0:
                i += 1

    a = int(a)
    b = int(b)

    match com:
        case "==":
            if a == b:
                return True
            else:
                return False

        case ">":
            if a > b:
                return True
            else:
                return False

        case "<":
            if a < b:
                return True
            else:
                return False

        case ">=":
            if a >= b:
                return True
            else:
                return False

        case "<=":
            if a <= b:
                return True
            else:
                return False

        case _:
            raise ValueError("error not valid comparitor")


def is_even(x):
    if x % 2:
        return False
    else:
        return True


def split_on_delimiters(text, delimiters):
    # Sort by length (longest first) so longer matches take priority
    delimiters = sorted(delimiters, key=len, reverse=True)
    pattern = "|".join(re.escape(d) for d in delimiters)
    # Split and keep the delimiters in the result
    chunks = re.split(f"({pattern})", text)
    # Remove empty strings that can appear between matches
    return [c for c in chunks if c != ""]


def count_sig_figs(part):
    m = re.match(r"\s*-?\d+\.?\d*(?:[eE][+-]?\d+)?", str(part))
    if not m:
        raise ValueError(f"Invalid number: {part!r}")
    s = str(Decimal(m.group(0))).replace(".", "").replace("-", "")
    return max(len(s.lstrip("0")), 1)


def min_sig_figs(inputs):
    counts = []
    for p in inputs:
        try:
            counts.append(count_sig_figs(p))
        except ValueError:
            pass
    return min(counts) if counts else None



def significant_figures(x, inputs):
    if x == 0:
        return 0
    n = min_sig_figs(inputs) or config.rounding_decimals
    decimals = n - 1 - math.floor(math.log10(abs(x)))
    result = round(x, decimals)
    return int(result) if decimals <= 0 else result


def round_pH(x, inputs):
    n = min_sig_figs(inputs) or config.rounding_decimals
    return f"{x:.{n}f}"




class FunctionPlot:
    def __init__(self,exprs, start =-10,end=10):
        x = sympy.Symbol("x")
        for expr in exprs:
            if expr.free_symbols - {x}:
                raise ValueError("Funktionerne kan kun bruge x som variabel")
            
        self.functions = [{"js":sympy.jscode(expr),"label" : sympy.latex(expr)} for expr in exprs]
        self.start = start
        self.end = end









def regretion(f,freturn,params,xs,ys,p0 = None):
    fit = {}
    popt, pcov = curve_fit(f,xs,ys,p0 = p0,maxfev = 100000)
    for i,part in enumerate(params): fit[part] = popt[i]
    result = freturn.subs(fit)
    rounded = result.xreplace({n: sympy.Float(n, 4) for n in result.atoms(sympy.Float)})
    residuals = np.array(ys) - f(np.array(xs), *popt)
    rmse = np.sqrt(np.mean(residuals**2))
    r2 = 1 - np.sum(residuals**2) / np.sum((np.array(ys) - np.mean(ys))**2)


    fig = Figure(figsize=(5, 4))
    fig.patch.set_facecolor("#404040")
    ax = fig.add_subplot(111)
    ax.set_facecolor("#323232")

    line_x = np.linspace(min(xs), max(xs), 400)
    ax.plot(line_x, f(line_x, *popt), color="#00d9ff", linewidth=2.2, label=f"$y = {sympy.latex(rounded)}$\n$R^2 = {r2:.4f}$\nRMSE = {rmse:.4g}")
    ax.scatter(xs, ys, color="#ffffff", s=30, zorder=5)

    legend = ax.legend(facecolor="#1e1e1e", edgecolor="#555566", handlelength=0, handletextpad=0)
    for text in legend.get_texts():
        text.set_color("white")

    ax.grid(True, color="#1F1F28", alpha=0.5)
    ax.set_xlabel("x", color="white")
    ax.set_ylabel("y", color="white")
    ax.tick_params(colors="white")
    for spine in ax.spines.values():
        spine.set_color("#555566")

    fig.tight_layout()
    return fig

    
    

    



