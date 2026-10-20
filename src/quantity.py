import pandas as pd
import utils
import ast
import re
import requests
from pathlib import Path
from path import resource_path
from platformdirs import user_data_dir

SHEET_ID = "1sGcaYTae8MoDOXOcbRd5Tvq8V5aVnvtHgwUt3cDfXng"
GID = "0"

url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID}"


_cache = {"df": None, "unit_data": None}

CACHE_DIR = Path(user_data_dir("fihsih calc",appauthor=False))
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


PREFIXES = {
    "Y": 1e24, "Z": 1e21, "E": 1e18, "P": 1e15, "T": 1e12, "G": 1e9, "M": 1e6,
    "k": 1e3, "h": 1e2, "da": 1e1, "d": 1e-1, "c": 1e-2, "m": 1e-3,
    "µ": 1e-6, "μ": 1e-6, "n": 1e-9, "p": 1e-12, "f": 1e-15, "a": 1e-18, "z": 1e-21, "y": 1e-24,
}


def lookup_unit(name):
    unit_data = retrive_units()
    if name in unit_data:
        return unit_data[name]

    for prefix in sorted(PREFIXES,key = len, reverse=True):
        base = name[len(prefix):]
        if name.startswith(prefix) and base in unit_data and "^" not in base:
            data = unit_data[base]
            return {"factor": PREFIXES[prefix]*data["factor"],"base_units": data["base_units"]}
    raise ValueError(f"unknown unit {name}")


def known_unit_names():
    table = retrive_units()
    names = set(table)
    names.update(p + u for p in PREFIXES for u in table if "^" not in u)
    return list(names)

class quantity:
    def __init__(self, value, units):
        self.value = value
        self.units = units

    # mulitiplication for  quantities
    def __mul__(self, other):
        new_value = self.value * other.value
        new_units = self.units.copy()

        for unit, power in other.units.items():
            if unit in new_units:
                new_units[unit] += power
            else:
                new_units[unit] = power
        return quantity(new_value, self._clean(new_units))

    # divides quantities
    def __truediv__(self, other):
        new_value = self.value / other.value
        new_units = self.units.copy()

        for unit, power in other.units.items():
            if unit in new_units:
                new_units[unit] -= power
            else:
                new_units[unit] = 0 - power
        return quantity(new_value, self._clean(new_units))

    # expoents for quanteties
    def __pow__(self, power):
        if isinstance(power, quantity):
            if power.units:  # has units → invalid
                raise ValueError("Exponent must be unitless")
            power = power.value  # extract scalar

        new_value = self.value**power

        new_units = {}
        for unit, exp in self.units.items():
            new_units[unit] = exp * power

        return quantity(new_value, self._clean(new_units))

    # addition for quanteties
    def __add__(self, other):
        if self.units == other.units:
            new_value = self.value + other.value
            return quantity(new_value, self._clean(self.units))
        else:
            raise ValueError("Error cant add diffrent units")

    # subtraction for quantities
    def __sub__(self, other):
        if self.units == other.units:
            new_value = self.value - other.value
            return quantity(new_value, self._clean(self.units))
        else:
            raise ValueError("Error cant subtract diffrent units")

    # returns quantities as readeble data
    def __str__(self):
        units = self.units

        numerator = []
        denominator = []

        for name, power in units.items():
            if utils.is_positive(power):
                if power == 1:
                    numerator.append(f"{name}")
                else:
                    numerator.append(f"{name}^{power:g}")

            if not utils.is_positive(power):
                if power == -1:
                    denominator.append(f"{name}")
                else:
                    denominator.append(f"{name}^{-power:g}")

        if len(numerator) > 0 and len(denominator) > 0:
            unit = f'{"*".join(numerator)}/{"*".join(denominator)}'
        elif len(numerator) > 0 and len(denominator) == 0:
            unit = f'{"*".join(numerator)}'
        elif len(numerator) == 0 and len(denominator) > 0:
            unit = f'1/{"*".join(denominator)}'
        else:
            unit = ""
        if unit == "":
            return f"{self.value}"
        else:
            return f"{self.value} {unit}"

    def __repr__(self):
        return f"value: {self.value} unit: {self.units}"

    def __eq__(self, other):

        if not isinstance(other, quantity):
            return NotImplemented
        return (self.value, self.units) == (other.value, other.units)

    # converts a quantity to si units
    @staticmethod
    def si_convert(q):
        value = q.value
        new_units = {}

        for unit_name, power in q.units.items():
            
            try:
                data = lookup_unit(unit_name)
            except ValueError: 
                raise ValueError(f'Ukendt enhed: {unit_name}')

            value *= data["factor"] ** power

            for base_unit, base_pow in data["base_units"].items():
                if base_unit in new_units:
                    new_units[base_unit] += base_pow * power
                else:
                    new_units[base_unit] = base_pow * power
        result = quantity(value, quantity._clean(new_units))
        return result

    @staticmethod
    def unit_convert(q, unit):
          
        target = quantity.quantity_convert(1, unit)

        if not target.units:
            raise ValueError(f"kan ikke parse unit: {unit}")

        source_si = quantity.si_convert(q)
        target_si = quantity.si_convert(target)

        if source_si.units != target_si.units:
            raise ValueError(
                f"cannot convert {q.units} to {unit}"
            )

        new_value = source_si.value / target_si.value

        return quantity(new_value, target.units)







    @staticmethod
    def quantity_convert(value, unit):
        units = known_unit_names()
        delims = sorted(units, key=len, reverse=True)
        pattern = "|".join(re.escape(d) for d in delims)

        power_flip = 1

        unit_list = re.split(f"({pattern}|[*/^])", unit)
        unit_list = [part for part in unit_list if part != ""]

        unit_dict = {}
        for i, part in enumerate(unit_list):
            if part in units:
                if i < len(unit_list)- 1 and   unit_list[i + 1] == "^":
                    unit_dict[part] = float(unit_list[i + 2]) * power_flip
                else:
                    unit_dict[part] = power_flip
            elif part == "/":
                power_flip = -1
            else:
                continue

        return quantity(value,unit_dict)

    @staticmethod
    def _clean(units):
        return {u: p for u, p in units.items() if p != 0}



