import pytest
import utils


# --- significant figures ---

@pytest.mark.parametrize("number, expected", [
    ("0.00120", 3),     # leading zeros don't count, trailing zeros do
    ("2.50", 3),
    ("100", 3),
    ("-4.2", 2),
    ("5.", 1),
    ("  3.14", 3),
    ("1e-5", 1),
    ("1.50e-5", 3),
    ("12abc", 2),       # only the number at the start is read
    ("250[ml]", 3),     # so a unit after it is fine
    (3.14, 3),
    (2, 1),
])
def test_count_sig_figs(number, expected):
    assert utils.count_sig_figs(number) == expected


@pytest.mark.xfail(reason="str(Decimal) writes these in E-notation and the E, sign and exponent get counted")
@pytest.mark.parametrize("number", ["1.5e3", "1.2e-7"])
def test_count_sig_figs_scientific_notation(number):
    assert utils.count_sig_figs(number) == 2


@pytest.mark.xfail(reason="the regex needs a digit before the point, but the parser accepts .5")
def test_count_sig_figs_without_leading_zero():
    assert utils.count_sig_figs(".5") == 1


def test_count_sig_figs_zero():
    assert utils.count_sig_figs("0") == 1


@pytest.mark.parametrize("number", ["abc", ""])
def test_count_sig_figs_invalid(number):
    with pytest.raises(ValueError, match="Invalid number"):
        utils.count_sig_figs(number)


@pytest.mark.parametrize("x, inputs, expected", [
    (3.14159, ["2.0", "1.234"], 3.1),     # the least precise input decides
    (-3.14159, ["2.0"], -3.1),
    (1234.5, ["1.2"], 1200),
    (12345, ["1.2345"], 12345),
    (0.000123456, ["1.23"], 0.000123),
    (3.5, ["1"], 4),
    (0, ["1"], 0),
])
def test_significant_figures(x, inputs, expected):
    assert utils.significant_figures(x, inputs) == expected


def test_significant_figures_gives_int_without_decimals():
    assert type(utils.significant_figures(1234.5, ["1.2"])) is int
    assert type(utils.significant_figures(3.14159, ["2.0"])) is float


@pytest.mark.xfail(reason="round() rounds a half to the nearest even digit (2.5 -> 2), school maths rounds up")
@pytest.mark.parametrize("x, inputs, expected", [
    (2.5, ["1"], 3),
    (0.125, ["0.50"], 0.13),
])
def test_significant_figures_rounds_half_up(x, inputs, expected):
    assert utils.significant_figures(x, inputs) == expected


# --- comparison ---

@pytest.mark.parametrize("text, expected", [
    ("3>2", True),
    ("2>3", False),
    ("2<3", True),
    ("3<2", False),
    ("3==3", True),
    ("3==4", False),
    ("3>=3", True),
    ("2>=3", False),
    ("3<=3", True),
    ("4<=3", False),
    (" 10 > 9 ", True),
])
def test_comparison(text, expected):
    assert utils.comparison(text) is expected


@pytest.mark.parametrize("text", ["3!=2", "3=3"])
def test_comparison_invalid_operator(text):
    with pytest.raises(ValueError, match="not valid comparitor"):
        utils.comparison(text)


@pytest.mark.xfail(reason="the decimal point is read but the number is then passed to int()")
def test_comparison_with_decimals():
    assert utils.comparison("1.5>1") is True


# --- small helpers ---

@pytest.mark.parametrize("x, expected", [
    (0, True), (2, True), (-2, True), (4.0, True),
    (1, False), (-3, False), (2.5, False),
])
def test_is_even(x, expected):
    assert utils.is_even(x) is expected


@pytest.mark.parametrize("x, expected", [
    (1, True), (0, True), (1e-9, True),     # 0 counts as positive
    (-0.5, False), (-1, False),
])
def test_is_positive(x, expected):
    assert utils.is_positive(x) is expected


@pytest.mark.parametrize("text, delimiters, expected", [
    ("a->b+c", ["->", "+"], ["a", "->", "b", "+", "c"]),
    ("a->b", ["-", "->"], ["a", "->", "b"]),             # longest delimiter wins
    ("a.b*c", [".", "*"], ["a", ".", "b", "*", "c"]),    # regex characters are escaped
    ("a++b", ["+"], ["a", "+", "+", "b"]),
    ("+a+", ["+"], ["+", "a", "+"]),
    ("abc", ["+"], ["abc"]),
    ("", ["+"], []),
])
def test_split_on_delimiters(text, delimiters, expected):
    assert utils.split_on_delimiters(text, delimiters) == expected


def test_config_is_loaded():
    assert isinstance(utils.config.rounding_decimals, int)
   