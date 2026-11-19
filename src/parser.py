import re
from quantity import quantity
import math
from path import resource_path
import json
from types import SimpleNamespace
from decimal import Decimal, ROUND_HALF_UP
from mat import Vector
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
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "Arcsin": math.asin,
    "Arccos": math.acos,
    "Arctan": math.atan,
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
    "Round": lambda x, n=0: float(Decimal(str(x)).quantize(Decimal(1).scaleb(-int(n)), rounding=ROUND_HALF_UP)),
    "Degrees": math.degrees,
    "Radians": math.radians,
    "Gamma": math.gamma,
    "Erf": math.erf,
}

CONSTANTS = {
            "π": math.pi,
            "ℯ": math.e,
            "𝑐": (2.99792458, "m/s"),
            "𝑔": (9.82, "m/s^2"),
            "𝐺": (6.674e-11,"N m^2/kg^2"),
            "ℎ": (6.626e-34,"J s"),
            "𝑒": (1.602e-19, "A s"),
            "𝑘": (1.381e-23, "J/K"),
            "𝑁": (6.022e23,"/mol"),
            "𝑅": (8.314, "J/mol K"),
            "𝐹": (96485, "A s/mol"),
            "𝜀": (8.854e-12, "A^2 s^4/kg m^3"),
            "𝜇": (1.2566e-6, "N/A^2"),
            "𝜎": (5.670e-8, "W/m^2 K^4"),
            "𝑚": (9.109e-31, "kg"),
            "𝑝": (1.6726e-27,"kg"),
            "𝐾": (1.0e-14, "mol^2/L^2"),
            "𝑉": (24.5, "L/mol")
            }

VECTOR_FUNCTIONS = {
    "Abs": abs,
    "Det": Vector.det,
    "EnhedsVektor": Vector.enhedsvektor,
    "VinkelVektor": lambda a, b: math.degrees(Vector.vinkel_mellem_vektorer(a, b)),
    "TværVektor": Vector.tværvektor,
    "Projektion": Vector.projektion,
}



TOKEN_RE = re.compile(
    r"\s*(?:"
    r"(?P<number>(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?)"
    r"|(?P<unit>°?[^\W\d_][^\W_]*)"
    r"|(?P<op>[-+*/^(),{}×])"
    r")"
)


def tokenise(text):
    tokens = []
    pos = 0
    text = text.rstrip()
    while pos < len(text):
        m = TOKEN_RE.match(text, pos)
        if not m or m.end() == pos:
            raise ValueError(f"Kan ikke læse '{text[pos:].strip()[:1]}' i '{text}'")
        kind = m.lastgroup
        tokens.append((kind, m.group(kind)))
        pos = m.end()
    return tokens


def scalar(q):
    if isinstance(q, Vector):
        raise ValueError("en vektor kan ikke indeholde en vektor")
    if q.dimension:
        raise ValueError("en vektor kan ikke have enheder")
    return q.value


def multiply(a, b, op):
    if isinstance(a, Vector) and isinstance(b, Vector):
        if op == "/":
            raise ValueError("man kan ikke dividere med en vektor")
        return Vector.cross_product(a,b) if op == "×" else quantity(Vector.dot_product(a,b),{},{})
    if isinstance(b, Vector):
        if op == "/":
            raise ValueError("man kan ikke dividere med en vektor")
        return Vector.scalar_product(scalar(a),b)
    if isinstance(a, Vector):
        return Vector.scalar_product(1 / scalar(b) if op == "/" else scalar(b), a)
    return a / b if op == "/" else a * b


def vector_function(name, values):
    if name not in VECTOR_FUNCTIONS or not all(isinstance(v, Vector) for v in values):
        raise ValueError(f"{name} kan ikke tage imod en vektor")
    result = VECTOR_FUNCTIONS[name](*values)
    return result if isinstance(result, Vector) else quantity(float(result), {}, {})



class _Parser:
    def __init__(self, text, functions = None):
        self.functions = {**FUNCTIONS, **(functions or {})}
        self.text = text
        self.tokens = tokenise(text)
        self.i = 0

    def peek(self):
        return self.tokens[self.i] if self.i < len(self.tokens) else (None, None)

    def take(self):
        tok = self.peek()
        self.i += 1
        return tok

    def expect_end(self):
        kind, value = self.peek()
        if value == ",":
            raise ValueError("brug punktum som decimal ikke komma")
        if kind is not None:
            raise ValueError(f"Uventet '{value}' i '{self.text}'")

    def expr(self):
        result = self.term()
        while self.peek() in (("op", "+"), ("op", "-")):
            op = self.take()[1]
            right = self.term()
            if isinstance(result, Vector) != isinstance(right, Vector):
                raise ValueError("man kan ikke bruge + eller - mellem et tal og en vektor")
            result = result + right if op == "+" else result - right
        return result

    def term(self):
        result = self.implicit()
        while self.peek() in (("op", "*"), ("op", "/"),("op","×")):
            op = self.take()[1]
            right = self.implicit()
            result = multiply(result, right, op)
        return result

    def implicit(self):
        result = self.unary()
        while True:
            kind, value = self.peek()
            if kind == "unit" or (kind, value) in (("op", "("), ("op", "{")):
                result = multiply(result, self.power(), "*")
            elif kind == "number":
                raise ValueError(f"Mangler et regnetegn før '{value}' i '{self.text}'")
            else:
                return result

    def unary(self):
        if self.peek() in (("op", "-"), ("op", "+")):
            op = self.take()[1]
            value = self.unary()
            if isinstance(value, Vector):
                return Vector.scalar_product(-1, value) if op == "-" else value
            return quantity(-value.value, value.dimension, value.current_units) if op == "-" else value
        return self.power()

    def power(self):
        base = self.atom()
        if self.peek() == ("op", "^"):
            self.take()
            exponent = self.exponent()
            if exponent.dimension:
                raise ValueError("En eksponent kan ikke have en enhed")
            p = exponent.value
            return base ** (int(p) if float(p).is_integer() else p)
        return base

    def exponent(self):
        if self.peek() in (("op", "-"), ("op", "+")):
            op = self.take()[1]
            value = self.exponent()
            return quantity(-value.value, value.dimension, value.current_units) if op == "-" else value
        return self.power()


    def group(self):
        self.take()
        result = self.expr()
        if self.take() != ("op", ")"):
            raise ValueError(f'mangler ")" i {self.text}')
        return result

    def args(self, end = ")"):
        self.take()
        result = [self.expr()]
        while self.peek() == ("op",","):
            self.take()
            result.append(self.expr())
        if self.take() != ("op", end):
            raise ValueError(f'mangler "{end}" i {self.text}')
        return result

    def atom(self):
        if self.peek() == ("op","("):
            return self.group()
        if self.peek() == ("op","{"):
            return Vector([str(scalar(v)) for v in self.args("}")])
        kind, value = self.take()
        if kind == "number":
            return quantity(float(value), {}, {})
        if kind == "unit" and value in CONSTANTS:
            number, unit = CONSTANTS[value]
            return quantity.create_quantity(number, unit)
        if kind == "unit" and self.peek() == ("op","("):
            if value == "sqrt":
                return self.group() ** 0.5
            if value in self.functions or value in VECTOR_FUNCTIONS:
                values = self.args()
                if any(isinstance(v, Vector) for v in values):
                    return vector_function(value, values)
                if value not in self.functions:
                    raise ValueError(f"{value} skal have vektorer")
                if any(v.dimension for v in values):
                     raise ValueError(f'{value} kan ikke tage imod enhed')
                return quantity(self.functions[value](*(v.value for v in values)),{},{})
            raise ValueError(f'Ukendt funktion "{value}"')

                   

        if kind == "unit":
            return quantity.create_quantity(1.0, value)
        if kind is None:
            raise ValueError(f'udtrykket slutter for tidligt: "{self.text}"')
        raise ValueError(f'uventet "{value}" i {self.text}')

def evaluate(equation,functions = None):
    if not equation.strip():
        raise ValueError("Tomt udtryk")

    p = _Parser(equation,functions)
    result = p.expr()
    p.expect_end()
    return result
