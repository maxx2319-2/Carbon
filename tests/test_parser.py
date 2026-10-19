import pytest
import parser
from quantity import quantity as Q


def ev(text):
    return str(parser.evaluate(text))


@pytest.mark.parametrize("text, expected", [
    ("1 + 1", "2.0"),
    ("2+3*4", "14.0"),
    ("(2+3)*4", "20.0"),
    ("10-4-3", "3.0"),      # left to right
    ("8/4/2", "1.0"),
    ("2^3", "8.0"),
    ("2^3^2", "512.0"),     # right to left: 2^(3^2)
    ("-2^2", "-4.0"),       # ^ before minus
    ("(-2)^2", "4.0"),
    ("2^-1", "0.5"),
    ("2^+2", "4.0"),
    ("2^0", "1.0"),
    ("2^(1/2)", "1.4142135623730951"),
    ("-4", "-4.0"),
    ("--5", "5.0"),
    ("+5", "5.0"),
    ("2*-3", "-6.0"),
    ("-(3)", "-3.0"),
])
def test_arithmetic(text, expected):
    assert ev(text) == expected


@pytest.mark.parametrize("text, expected", [
    ("1e3", "1000.0"),
    ("1.5E-2", "0.015"),
    (".5", "0.5"),
    ("5.", "5.0"),
    ("  4  ", "4.0"),
    ("4\t", "4.0"),
])
def test_number_formats(text, expected):
    assert ev(text) == expected


@pytest.mark.parametrize("text, expected", [
    ("2(3)", "6.0"),
    ("2(3+1)", "8.0"),
    ("(1+1)(2+2)", "8.0"),
    ("3m", "3.0 m"),
    ("3 m", "3.0 m"),
    ("1 m/2 s", "0.5 m/s"),     # "2 s" sticks together before the division
])
def test_implicit_multiplication(text, expected):
    assert ev(text) == expected


@pytest.mark.parametrize("text, expected", [
    ("2*3 m", "6.0 m"),
    ("10 km", "10.0 km"),
    ("2 m^2", "2.0 m^2"),       # ^ only applies to the unit
    ("(2 m)^2", "4.0 m^2"),
    ("2 m*3 s", "6.0 m*s"),
    ("1 m/(2 s)", "0.5 m/s"),
    ("m/m", "1.0"),
    ("2 m - 2 m", "0.0 m"),
    ("km/timer", "1.0 km/timer"),
    ("3 °C", "3.0 °C"),
    ("10 µm", "10.0 µm"),
])
def test_units(text, expected):
    assert ev(text) == expected


def test_units_are_kept_as_typed():
    assert parser.evaluate("5 km") == Q(5.0, {"km": 1})


@pytest.mark.parametrize("text, message", [
    ("1,5", "punktum"),
    ("", "Tomt udtryk"),
    ("   ", "Tomt udtryk"),
    ("(2+3", r"Mangler '\)'"),
    ("2)", r"Uventet '\)'"),
    ("()", r"Uventet '\)'"),
    ("*2", r"Uventet '\*'"),
    ("2*", "slutter for tidligt"),
    ("2^", "slutter for tidligt"),
    ("2 3", "Mangler et regnetegn før '3'"),
    ("2..3", "Mangler et regnetegn"),
    ("2 $", r"Kan ikke læse '\$'"),
    ("1, 5", "Kan ikke læse ','"),
    ("m^(1 s)", "eksponent kan ikke have en enhed"),
    ("1 m + 1 s", "diffrent units"),
])
def test_errors(text, message):
    with pytest.raises(ValueError, match=message):
        parser.evaluate(text)


def test_division_by_zero():
    with pytest.raises(ZeroDivisionError):
        parser.evaluate("1/0")


@pytest.mark.xfail(reason="a negative number to a fractional power gives a complex number instead of an error")
def test_negative_number_to_fractional_power():
    with pytest.raises(ValueError):
        parser.evaluate("(-8)^(1/3)")


def test_tokenise():
    assert parser.tokenise("2.5 km^2/(3 s)") == [
        ("number", "2.5"), ("unit", "km"), ("op", "^"), ("number", "2"), ("op", "/"),
        ("op", "("), ("number", "3"), ("unit", "s"), ("op", ")"),
    ]


def test_tokenise_scientific_notation_and_spaces():
    assert parser.tokenise("  1e-3   m ") == [("number", "1e-3"), ("unit", "m")]
