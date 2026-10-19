import re
from quantity import quantity



TOKEN_RE = re.compile(
    r"\s*(?:"
    r"(?P<number>(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?)"
    r"|(?P<unit>°?[^\W\d_]+)"
    r"|(?P<op>[-+*/^()])"
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


class _Parser:
    def __init__(self, text):
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
        if kind is not None:
            raise ValueError(f"Uventet '{value}' i '{self.text}'")

    def expr(self):
        result = self.term()
        while self.peek() in (("op", "+"), ("op", "-")):
            op = self.take()[1]
            right = self.term()
            result = result + right if op == "+" else result - right
        return result

    def term(self):
        result = self.implicit()
        while self.peek() in (("op", "*"), ("op", "/")):
            op = self.take()[1]
            right = self.implicit()
            result = result * right if op == "*" else result / right
        return result

    def implicit(self):
        result = self.unary()
        while True:
            kind, value = self.peek()
            if kind == "unit" or (kind, value) == ("op", "("):
                result = result * self.power()
            elif kind == "number":
                raise ValueError(f"Mangler et regnetegn før '{value}' i '{self.text}'")
            else:
                return result

    def unary(self):
        if self.peek() in (("op", "-"), ("op", "+")):
            op = self.take()[1]
            value = self.unary()
            return quantity(-value.value, value.units) if op == "-" else value
        return self.power()

    def power(self):
        base = self.atom()
        if self.peek() == ("op", "^"):
            self.take()
            exponent = self.exponent()
            if exponent.units:
                raise ValueError("En eksponent kan ikke have en enhed")
            p = exponent.value
            return base ** (int(p) if float(p).is_integer() else p)
        return base

    def exponent(self):
        if self.peek() in (("op", "-"), ("op", "+")):
            op = self.take()[1]
            value = self.exponent()
            return quantity(-value.value, value.units) if op == "-" else value
        return self.power()

    def atom(self):
        kind, value = self.take()
        if kind == "number":
            return quantity(float(value), {})
        if kind == "unit":
            return quantity(1.0, {value: 1})
        if (kind, value) == ("op", "("):
            result = self.expr()
            if self.take() != ("op", ")"):
                raise ValueError(f"Mangler ')' i '{self.text}'")
            return result
        if kind is None:
            raise ValueError(f"Udtrykket slutter for tidligt: '{self.text}'")
        raise ValueError(f"Uventet '{value}' i '{self.text}'")


def evaluate(equation):
    if re.search(r"\d,\d", equation):
        raise ValueError("Brug punktum som decimal tal ikke komma")
    if not equation.strip():
        raise ValueError("Tomt udtryk")

    p = _Parser(equation)
    result = p.expr()
    p.expect_end()
    return result
