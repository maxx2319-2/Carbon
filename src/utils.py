import re
import json
from types import SimpleNamespace
from decimal import Decimal
import math
import sympy
import numpy as np
from matplotlib.figure import Figure


from path import resource_path

with open(resource_path("config.json")) as f:
    config = json.load(f, object_hook=lambda d: SimpleNamespace(**d))


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




def function_figure(exprs, start=-10, end =10):
    x = sympy.Symbol("x")
    xs = np.linspace(start, end, 400)
    colors = ["#00d9ff", "#ff6ec7", "#ffd166", "#06ffa5", "#c77dff", "#ff9e6d"]

    fig = Figure(figsize=(5, 4))
    fig.patch.set_facecolor("#404040")
    ax = fig.add_subplot(111)
    ax.set_facecolor("#323232")
    for i, expr in enumerate(exprs):
        f = sympy.lambdify(x, expr, "numpy")
        ax.plot(xs, f(xs) * np.ones_like(xs), color=colors[i % len(colors)], linewidth=2.2, label=f"${sympy.latex(expr)}$")
    ax.axhline(0, color="#858585", linewidth=0.8)
    ax.axvline(0, color="#858585", linewidth=0.8)
    ax.grid(True, color="#1F1F28", alpha=0.5)
    ax.tick_params(colors="white")
    for spine in ax.spines.values():
        spine.set_color("#555566")
    legend = ax.legend(facecolor="#1e1e1e", edgecolor="#555566")
    for text in legend.get_texts():
        text.set_color("white")
    fig.tight_layout()
    return fig
