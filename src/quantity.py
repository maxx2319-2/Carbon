import pandas as pd
import utils
import ast
import re
import math
import requests
from pathlib import Path
from path import resource_path
from platformdirs import user_data_dir

SHEET_ID = "1sGcaYTae8MoDOXOcbRd5Tvq8V5aVnvtHgwUt3cDfXng"

url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv"


_cache = {"df": None, "unit_data": None}

CACHE_DIR = Path(user_data_dir("Carbon",appauthor=False))
CACHE_FILE = CACHE_DIR / "units.csv"
BUNDLED_FILE = resource_path("Assets/units.csv")

def update_unit_file():
    try:
        r = requests.get(url,timeout=10)
        r.raise_for_status()
        CACHE_DIR.mkdir(parents=True,exist_ok=True)
        tmp = CACHE_FILE.with_suffix(".tmp")
        tmp.write_bytes(r.content)
        if "unit" not in pd.read_csv(tmp).columns:
            raise ValueError("Error in unit data")
        tmp.replace(CACHE_FILE)
    except Exception:
        pass

def _get_df():
    if _cache["df"] is None:
        source = CACHE_FILE if CACHE_FILE.exists() else BUNDLED_FILE
        _cache["df"] = pd.read_csv(source)
        _cache["unit_data"] = None
    return _cache["df"]

def retrive_units():
    if _cache["unit_data"] is not None:
        return _cache["unit_data"]

    df = _get_df()
    unit_data = {}

    for row in df.itertuples():
        if pd.isna(row.unit):
            continue
        unit_name = str(row.unit).strip()
        try:
            factor = float(str(row.ratiotosi).strip().replace(",", "."))
        except (ValueError, TypeError):
            continue
        if factor <= 0:
            continue
        try:
            base_units = ast.literal_eval(row.dimension_dict)
        except (ValueError, SyntaxError):
            continue
        unit_data[unit_name] = {"factor": factor, "base_units": base_units}

    _cache["unit_data"] = unit_data
    return unit_data

PREFERRED = {
    "N":  {"M": 1, "L": 1, "T": -2},
    "J":  {"M": 1, "L": 2, "T": -2},
    "W":  {"M": 1, "L": 2, "T": -3},
    "Pa": {"M": 1, "L": -1, "T": -2},
    "C":  {"I": 1, "T": 1},
    "V":  {"M": 1, "L": 2, "T": -3, "I": -1},
    "Ω":  {"M": 1, "L": 2, "T": -3, "I": -2},
    "F":  {"M": -1, "L": -2, "T": 4, "I": 2},
    "T":  {"M": 1, "T": -2, "I": -1},
    "Wb": {"M": 1, "L": 2, "T": -2, "I": -1},
    "H":  {"M": 1, "L": 2, "T": -2, "I": -2},
    "S":  {"M": -1, "L": -2, "T": 3, "I": 2},
}


PREFIXES = {
    "Y": 1e24, "Z": 1e21, "E": 1e18, "P": 1e15, "T": 1e12, "G": 1e9, "M": 1e6,
    "k": 1e3, "h": 1e2, "da": 1e1, "d": 1e-1, "c": 1e-2, "m": 1e-3,
    "µ": 1e-6, "μ": 1e-6, "n": 1e-9, "p": 1e-12, "f": 1e-15, "a": 1e-18, "z": 1e-21, "y": 1e-24,
}

SI_TO_DIMENSION = {
    "m": "L",
    "kg": "M",
    "s": "T",
    "A": "I",
    "K": "Θ",
    "mol": "N",
    "cd": "J",
}

DIMENSION_TO_SI = {v: k for k, v in SI_TO_DIMENSION.items()}


def lookup_unit(name):
    unit_data = retrive_units()
    if name in unit_data:
        return unit_data[name]

    for prefix in sorted(PREFIXES,key = len, reverse=True):
        base = name[len(prefix):]
        if name.startswith(prefix) and base in unit_data and "^" not in base:
            data = unit_data[base]
            return {"factor": PREFIXES[prefix]*data["factor"],"base_units": data["base_units"]}
    raise ValueError(f"ukendt enhed {name}")


def known_unit_names():
    table = retrive_units()
    names = set(table)
    names.update(p + u for p in PREFIXES for u in table if "^" not in u)
    return list(names)

class quantity:
    def __init__(self, value, dimension, current_units):
        self.dimension = dimension
        self.value = value
        self.current_units = current_units


    @staticmethod
    def create_quantity(value, unit):
        current_units = {}
        flip = 1
        for op, u, exp in re.findall(r"(/?)([^\W\d]+)(?:\^(-?[\d.]+))?", unit):
            if op:
                flip = -1
            current_units[u] = current_units.get(u, 0) + float(exp or 1) * flip

        dimension = {}
        for u, exp in current_units.items():
            for dim, power in lookup_unit(u)["base_units"].items():
                dimension[dim] = dimension.get(dim, 0) + power * exp

        return quantity(value, quantity._clean(dimension), current_units)



    # mulitiplication for  quantities
    def __mul__(self, other):
        value = self.value*other.value

        dimension = dict(self.dimension)
        units = dict(self.current_units)
        for dim,exp in other.dimension.items():
            if dim in dimension:
                dimension[dim] = dimension[dim] + exp
            else:
                dimension[dim] = exp

        for unit,exp in other.current_units.items():
            if unit in units:
                units[unit] = units[unit] + exp
            else:
                units[unit] = exp

        return quantity(value,quantity._clean(dimension),quantity._clean(units))
       
    # divides quantities
    def __truediv__(self, other):
        value = self.value/other.value
        dimension = dict(self.dimension)
        units = dict(self.current_units)
        for dim,exp in other.dimension.items():
            if dim in dimension:
                dimension[dim] = dimension[dim] - exp
            else:
                dimension[dim] = -exp

        for unit,exp in other.current_units.items():
            if unit in units:
                units[unit] = units[unit] - exp
            else:
                units[unit] = -exp

        return quantity(value,quantity._clean(dimension),quantity._clean(units))
       

    # expoents for quanteties
    def __pow__(self, power):
        dimension = {dim: exp * power for dim, exp in self.dimension.items()}
        units = {unit: exp * power for unit, exp in self.current_units.items()}
        return quantity(self.value ** power, quantity._clean(dimension), quantity._clean(units))
    # addition for quanteties
    def __add__(self, other):
        if self.dimension != other.dimension:
            raise ValueError(f"man kan ikke lægge {self.current_units} sammen med {other.current_units}")
        other_value = (quantity.si_convert(other).value)/(quantity.si_convert(quantity(1, self.dimension, self.current_units)).value)
        value = self.value + other_value

        return quantity(value, self.dimension, self.current_units)

    # subtraction for quantities
    def __sub__(self, other):
        if self.dimension != other.dimension:
            raise ValueError(f"man kan ikke trække {other.current_units} fra {self.current_units}")
        other_value = (quantity.si_convert(other).value)/(quantity.si_convert(quantity(1, self.dimension, self.current_units)).value)
        value = self.value - other_value

        return quantity(value, self.dimension, self.current_units)
    # returns quantities as readeble data
    def __str__(self):
        numerator = []
        denominator = []
        for unit, power in (self.current_units or {}).items():
            if power > 0:
                numerator.append(unit if power == 1 else f"{unit}^{power:g}")
            else:
                denominator.append(unit if power == -1 else f"{unit}^{-power:g}")

        if numerator and denominator:
            unit = f'{"*".join(numerator)}/{"*".join(denominator)}'
        elif numerator:
            unit = "*".join(numerator)
        elif denominator:
            unit = f'1/{"*".join(denominator)}'
        else:
            return f"{self.value}"
        return f"{self.value} {unit}"

    def __repr__(self):
        return f"quantity(value={self.value!r}, dimension={self.dimension!r}, current_units={self.current_units!r})"

    def __eq__(self, other):
        if not isinstance(other, quantity):
            return NotImplemented
        if self.dimension != other.dimension:
            return False
        return math.isclose(quantity.si_convert(self).value, quantity.si_convert(other).value)
    @staticmethod
    def si_convert(q):
        value = q.value
        for u, exp in q.current_units.items():
            value *= lookup_unit(u)["factor"] ** exp
        si_units = {DIMENSION_TO_SI[d]: p for d, p in q.dimension.items()}
        return quantity(value, q.dimension, si_units)
        
    @staticmethod
    def unit_convert(q, unit):
        target = quantity.create_quantity(1, unit)
        if q.dimension != target.dimension:
            raise ValueError(f"kan ikke omregne {q.current_units} til {unit}")
        value = quantity.si_convert(q).value / quantity.si_convert(target).value
        return quantity(value, q.dimension, target.current_units)

    @staticmethod
    def cost(d):
        return sum(abs(p) for p in d.values())

    @staticmethod
    def merge_units(q):
        value, units, first = q.value, {}, {}
        for u, exp in q.current_units.items():
            info = lookup_unit(u)
            key = tuple(sorted(info["base_units"].items()))
            if key in first:
                keep = first[key]
                value *= (info["factor"] / lookup_unit(keep)["factor"]) ** exp
                units[keep] += exp
            else:
                first[key] = u
                units[u] = exp
        return quantity(value, q.dimension, quantity._clean(units))

    @staticmethod
    def named_units(q):
        dim = dict(q.dimension)
        units = {}
        while True:
            best, best_cost = None, quantity.cost(dim)
            for name, d in PREFERRED.items():
                if name not in retrive_units():
                    continue
                for sign in (1, -1):
                    rest = quantity._clean({k: dim.get(k, 0) - sign * d.get(k, 0) for k in set(dim) | set(d)})
                    c = quantity.cost(rest) + 1
                    if c < best_cost:
                        best, best_cost = (name, sign, rest), c
            if best is None:
                break
            name, sign, dim = best
            units[name] = units.get(name, 0) + sign

        own = {}
        for u in q.current_units:
            base = lookup_unit(u)["base_units"]
            if len(base) == 1 and list(base.values())[0] == 1:
                own.setdefault(list(base)[0], u)
        named = bool(units)
        for k, p in dim.items():
            if named and k not in own:
                return q
            u = own.get(k, DIMENSION_TO_SI[k])
            units[u] = units.get(u, 0) + p

        value = quantity.si_convert(q).value / quantity.si_convert(quantity(1, q.dimension, units)).value
        return quantity(value, q.dimension, units)

    @staticmethod
    def simplify_units(q):
        merged = quantity.merge_units(q)
        named = quantity.named_units(q)
        return named if quantity.cost(named.current_units) < quantity.cost(merged.current_units) else merged


    @staticmethod
    def _clean(d):
        return {k: p for k, p in d.items() if p != 0}




