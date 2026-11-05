import parser
import utils
import chem
from quantity import quantity
import re
import biotek
import json
import sympy 
import keyword
from sympy import simplify
import numpy as np
from matplotlib.figure import Figure
import multiprocessing
from multiprocessing.pool import ThreadPool

from sympy.parsing.sympy_parser import parse_expr, standard_transformations, implicit_multiplication, convert_xor, split_symbols

from types import SimpleNamespace
from chem import pKa_values,pKb_values

from path import resource_path
from pathlib import Path



with open(resource_path("config.json")) as f:
    config = json.load(f, object_hook=lambda d: SimpleNamespace(**d))





def round_quantity(quant,inputs):
    value = utils.significant_figures(quant.value,inputs)
    return quantity(value,quant.dimension,quant.current_units)

CONSTANTS = ("e", "π")

SYMPY_FUNCTIONS = {
    "Ln": sympy.log,
    "Log": lambda a: sympy.log(a, 10),
    "Exp": sympy.exp,
    "Sin": lambda a: sympy.sin(a * sympy.pi / 180),
    "Cos": lambda a: sympy.cos(a * sympy.pi / 180),
    "Tan": lambda a: sympy.tan(a * sympy.pi / 180),
    "ArcSin": lambda a: sympy.asin(a) * 180 / sympy.pi,
    "ArcCos": lambda a: sympy.acos(a) * 180 / sympy.pi,
    "ArcTan": lambda a: sympy.atan(a) * 180 / sympy.pi,
    "sin":sympy.sin,
    "cos": sympy.cos,
    "tan": sympy.tan,
    "Arcsin": sympy.asin,
    "Arccos": sympy.acos,
    "Arctan": sympy.atan,
    "Sinh": sympy.sinh,
    "Cosh": sympy.cosh,
    "Tanh": sympy.tanh,
    "ArcSinh": sympy.asinh,
    "ArcCosh": sympy.acosh,
    "ArcTanh": sympy.atanh,
    "Cbrt": sympy.cbrt,
    "Abs": sympy.Abs,
    "Floor": sympy.floor,
    "Ceil": sympy.ceiling,
    "Degrees": lambda a: a * 180 / sympy.pi,
    "Radians": lambda a: a * sympy.pi / 180,
    "Integrate": sympy.integrate,
    "Diff": sympy.diff,
    "Limit": sympy.limit,
    "Summation": sympy.summation,

}
TRANSFORMATIONS = standard_transformations + (split_symbols, implicit_multiplication, convert_xor)
SAFE_GLOBALS = {
    "__builtins__": {},
    "Symbol": sympy.Symbol, "Integer": sympy.Integer, "Float": sympy.Float, "Rational": sympy.Rational, "Number": sympy.Number, "Function": sympy.Function,
    "integrate": sympy.integrate, "diff": sympy.diff, "limit": sympy.limit, "summation": sympy.summation,
    "sqrt": sympy.sqrt, "oo": sympy.oo, "pi": sympy.pi, "E": sympy.E,
}

def safe_parse(text, local_dict):
    if re.search(r"_|\.(?!\d)|[^\w\s+\-*/^(),.]", text):
        raise ValueError("Ugyldigt tegn i udtrykket")
    for name in re.findall(r"[^\W\d]\w*", text):
        if keyword.iskeyword(name):
            raise ValueError(f'Ukendt navn "{name}"')
    for name in re.findall(r"([^\W\d]\w+)\s*\(", text):
        if name not in local_dict and name not in SAFE_GLOBALS:
            raise ValueError(f'Ukendt funktion "{name}"')
    return parse_expr(text, local_dict=local_dict, global_dict=SAFE_GLOBALS, transformations=TRANSFORMATIONS)

class Variables:
    def __init__(self, value, var_type):
        self.value = str(value)
        self.var_type = str(var_type)

    def __str__(self):
        return f"{self.value} {self.var_type}"


class EV:
    def __init__(self):
        self.variables = {}
        self._pattern = None
        self._pattern_dirty = True
        self.functions = [
            "Help",
            "Afstem",
            "pH",
            "pOH",
            "EnhedKonvertering",
            "Loop",
            "Analyse",
            "BjerrumDiagram",
            "UdbytteProcent",
            "VolumenProcent",
            "MasseProcent",
            "DNATilPeptid",
            "RNATilPeptid",
            "MængdeBeregning",
            "Puffer",
            "pHTilKoncentration",
            "Løs",
            "Plot",
            "NumeriskLøs",
            "SystemLøs",
            "Simplificer",
            "Regression",
            "LinReg",
            "PropReg",
            "ExpReg",
            "KvadReg",
            "LogistReg",
            "HarmReg",

        ]

        self.error_text = {
            "Help" : "Help() or Help(function)",
            "Afstem": "Afstem(reaktion,opløsning(syre,base eller ingenting))",
            "pH": "pH(pKs eller syre/basenavn,Koncentration)",
            "pOH": "pOH(pKb eller syre/base navn,Koncentration)",
            "EnhedKonvertering": 'EnhedKonvertering(Mængde,ny Enhed eller "SI" for SI-enhed)',
            "Loop": "Loop(startlinje,slutlinje,antal gange)",
            "Analyse": "Analyse(molekyle)",
            "BjerrumDiagram": "Bjerrumdiagram(pKs1,pKs2,...)",
            "UdbytteProcent":"UdbytteProcent(Praktisk,Teoretisk)" ,
            "VolumenProcent":"VolumenProcent(Praktisk,Teoretisk)",
            "MasseProcent":"MasseProcent(Praktisk,Teoretisk)",
            "DNATilPeptid":"DNATilPeptid(DNA-streng)",
            "RNATilPeptid":"RNATilPeptid(RNA-streng)",
            "MængdeBeregning": "MængdeBeregning(m=..,n=..,etc)",
            "Puffer" : "Puffer(Syre koncentration,Base koncentration, pKs)",
            "pHTilKoncentration" : "pHTilKoncentration(pH)",
            "Løs" : "Løs(ligning, evt Interval = (start, slut))",
            "Plot" : "Plot(function 1,function 2,...,Interval = (x start , x slut) )",
            "NumeriskLøs" : "NumeriskLøs(function, variabel, evt gæt)",
            "SystemLøs" : "SystemLøs(ligning 1,ligning 2,ligning... , Variabler = {x, y, ...}, evt StartGæt = {1, 1, ...}, evt Interval = (start, slut))",
            "Simplificer" : "Simplificer(x)",
            "Regression" : "Regression(funktion af x, {x værdier}, {y værdier})",
            "LinReg" : "LinReg({x værdier}, {y værdier})",
            "PropReg" : "PropReg({x værdier}, {y værdier})",
            "ExpReg" : "ExpReg({x værdier}, {y værdier})",
            "KvadReg" : "KvadReg({x værdier}, {y værdier})",
            "LogistReg" : "LogistReg({x værdier}, {y værdier})",
            "HarmReg" : "HarmReg({x værdier}, {y værdier})",
        }

        self.help_text = {
            "Help": "Help() eller Help(funktion)\nViser alle funktioner, eller hjælp til én funktion.\nEks: Help(pH) ",
            "Afstem": "Afstem(reaktion, opløsning)\nAfstemmer en reaktion. Opløsning er syre, base eller udeladt.\nEks: Afstem(H2 + O2 -> H2O) ",
            "pH": "pH(pKs eller syrenavn eller basenavn, koncentration)\nBeregner pH for en syre eller base.\nEks: pH(4.76, 0.10) ",
            "pOH": "pOH(pKb eller basenavn eller syrenavn, koncentration)\nBeregner pOH for en base eller syre.\nEks: pOH(4.75, 0.10) ",
            "EnhedKonvertering": 'EnhedKonvertering(størrelse, ny enhed eller "SI")\nKonverterer en størrelse til en ny enhed eller til SI-enhed.\nEks: EnhedKonvertering(4[km],SI) ',
            "Loop": "Loop(startlinje, slutlinje, antal gange)\nKører linjerne fra start til slut flere gange. Variablen i tæller fra 0.\nEks: Loop(1, 3, 5) ",
            "Analyse": "Analyse(molekyle)\nViser empirisk formel, molar masse, DBE, antal atomer og masseprocent.\nEks: Analyse(C6H12O6) ",
            "BjerrumDiagram": "BjerrumDiagram(pKs1, pKs2, ..., export)\nTegner et Bjerrumdiagram ud fra pKs-værdier eller syrenavne. Skriv export for at åbne det i et nyt vindue.\nEks: BjerrumDiagram(2.15, 7.20, 12.35) ",
            "UdbytteProcent": "UdbytteProcent(praktisk, teoretisk)\nBeregner udbyttet i procent.\nEks: UdbytteProcent(4.5[g], 5[g]) ",
            "VolumenProcent": "VolumenProcent(praktisk, teoretisk)\nBeregner volumenprocent.\nEks: VolumenProcent(40[ml], 100[ml]) ",
            "MasseProcent": "MasseProcent(praktisk, teoretisk)\nBeregner masseprocent.\nEks: MasseProcent(12[g], 50[g]) ",
            "DNATilPeptid": "DNATilPeptid(DNA-streng)\nOversætter en DNA-streng til et peptid.\nEks: DNATilPeptid(ATGGCCTAA) ",
            "RNATilPeptid": "RNATilPeptid(RNA-streng)\nOversætter en RNA-streng til et peptid.\nEks: RNATilPeptid(AUGGCCUAA) ",
            "MængdeBeregning": "MængdeBeregning(m=.., n=.., ...)\nBeregner de manglende størrelser ud fra m, n, M, c, V og p .\nEks: MængdeBeregning(m=10[g], M=58.44[g/mol], V=0.5[l]) ",
            "Puffer": "Puffer(syrekoncentration, basekoncentration, pKs)\nBeregner pH i en puffer med pufferligningen.\nEks: Puffer(0.10, 0.10, 4.76) ",
            "pHTilKoncentration": "pHTilKoncentration(pH)\nBeregner [H3O+] og [OH-] ud fra pH.\nEks: pHTilKoncentration(3.5) ",
            "Løs": "Løs(ligning, Interval = (start, slut))\nLøser en ligning. Kan ikke tage imod enheder. Interval er valgfrit og finder alle løsninger i intervallet numerisk.\nEks: Løs(x^2 = 4) ",
            "Plot": "Plot(funktion 1, funktion 2, ..., Interval = (x start, x slut))\nTegner en eller flere funktioner. Interval er valgfrit.\nEks: PlotFunktion(x^2, Sin(x), Interval=(-5,5)) ",
            "NumeriskLøs": "NumeriskLøs(funktion, Variabel = x, StartGæt = 1)\nLøser en ligning numerisk ud fra et startgæt. StartGæt er valgfrit.\nEks: NumeriskLøs(Cos(x) = x, Variabel = x, StartGæt = 10) ",
            "SystemLøs": "SystemLøs(ligning 1, ligning 2, ..., Variabler = {x, y, ...}, StartGæt = {1, 1, ...}, Interval = (start, slut))\nLøser et ligningssystem med flere ubekendte. StartGæt er valgfrit og bruges, når systemet skal løses numerisk. Interval er valgfrit og finder alle løsninger, hvor den første variabel ligger i intervallet.\nEks: SystemLøs(x + y = 10, x - y = 2, Variabler = {x, y}) ",
            "Simplificer": "Simplificer(udtryk)\nUdregner et udtryk med kvadratrødder, brøker osv. til et decimaltal.\nEks: Simplificer(sqrt(12) + sqrt(27)) ",
            "Regression": "Regression(funktion af x, {x1, x2, ...}, {y1, y2, ...})\nFinder de ukendte konstanter i funktionen, så den passer bedst til datapunkterne. Viser grafen med forskrift, R^2 og RMSE.\nEks: Regression(ax^2 + b, {0, 1, 2, 3}, {1, 2, 5, 10}) ",
            "LinReg": "LinReg({x1, x2, ...}, {y1, y2, ...})\nLineær regression. Finder a og b i f(x) = ax + b. Viser grafen med forskrift, R^2 og RMSE.\nEks: LinReg({1, 2, 3, 4}, {3, 5, 7, 9}) ",
            "PropReg": "PropReg({x1, x2, ...}, {y1, y2, ...})\nProportional regression. Finder a i f(x) = ax. Viser grafen med forskrift, R^2 og RMSE.\nEks: PropReg({1, 2, 3, 4}, {2, 4, 6, 8}) ",
            "ExpReg": "ExpReg({x1, x2, ...}, {y1, y2, ...})\nEksponentiel regression. Finder a og b i f(x) = a*b^x. Viser grafen med forskrift, R^2 og RMSE.\nEks: ExpReg({0, 1, 2, 3}, {2, 6, 18, 54}) ",
            "KvadReg": "KvadReg({x1, x2, ...}, {y1, y2, ...})\nKvadratisk regression. Finder a, b og c i f(x) = ax^2 + bx + c. Viser grafen med forskrift, R^2 og RMSE.\nEks: KvadReg({0, 1, 2, 3}, {1, 2, 5, 10}) ",
            "LogistReg": "LogistReg({x1, x2, ...}, {y1, y2, ...})\nLogistisk regression. Finder a, b og c i f(x) = c/(1+a*Exp(-bx)). Viser grafen med forskrift, R^2 og RMSE.\nEks: LogistReg({0, 2, 4, 6, 8}, {1, 4.5, 8.3, 9.7, 9.96}) ",
            "HarmReg": "HarmReg({x1, x2, ...}, {y1, y2, ...})\nHarmonisk svingning. Finder amplituden A, vinkelfrekvensen ω, faseforskydningen φ og ligevægtslinjen k i f(x) = A*sin(ωx+φ)+k. Viser grafen med forskrift, R^2 og RMSE.\nEks: HarmReg({0, 1, 2, 3, 4, 5}, {2, 3.4, 3.1, 1.7, 0.6, 0.9}) ",
            "Ln": "Ln(x)\nNaturlig logaritme (grundtal e).\nEks: Ln(10) ",
            "Log": "Log(x)\nTitalslogaritme (grundtal 10).\nEks: Log(1000) ",
            "Exp": "Exp(x)\nEksponentialfunktionen e^x.\nEks: Exp(2) ",
            "Sin": "Sin(vinkel)\nSinus til en vinkel i grader.\nEks: Sin(30) ",
            "Cos": "Cos(vinkel)\nCosinus til en vinkel i grader.\nEks: Cos(60) ",
            "Tan": "Tan(vinkel)\nTangens til en vinkel i grader.\nEks: Tan(45) ",
            "ArcSin": "ArcSin(x)\nOmvendt sinus. Giver vinklen i grader.\nEks: ArcSin(0.5) ",
            "ArcCos": "ArcCos(x)\nOmvendt cosinus. Giver vinklen i grader.\nEks: ArcCos(0.5) ",
            "ArcTan": "ArcTan(x)\nOmvendt tangens. Giver vinklen i grader.\nEks: ArcTan(1) ",
            "sin": "sin(vinkel)\nSinus til en vinkel i radianer.\nEks: sin(1) ",
            "cos": "cos(vinkel)\nCosinus til en vinkel i radianer.\nEks: cos(1) ",
            "tan": "tan(vinkel)\nTangens til en vinkel i radianer.\nEks: tan(1) ",
            "Arcsin": "Arcsin(x)\nOmvendt sinus. Giver vinklen i radianer.\nEks: Arcsin(0.5) ",
            "Arccos": "Arccos(x)\nOmvendt cosinus. Giver vinklen i radianer.\nEks: Arccos(0.5) ",
            "Arctan": "Arctan(x)\nOmvendt tangens. Giver vinklen i radianer.\nEks: Arctan(1) ",
            "Sinh": "Sinh(x)\nHyperbolsk sinus.\nEks: Sinh(1) ",
            "Cosh": "Cosh(x)\nHyperbolsk cosinus.\nEks: Cosh(1) ",
            "Tanh": "Tanh(x)\nHyperbolsk tangens.\nEks: Tanh(1) ",
            "ArcSinh": "ArcSinh(x)\nOmvendt hyperbolsk sinus.\nEks: ArcSinh(1) ",
            "ArcCosh": "ArcCosh(x)\nOmvendt hyperbolsk cosinus. x skal være mindst 1.\nEks: ArcCosh(2) ",
            "ArcTanh": "ArcTanh(x)\nOmvendt hyperbolsk tangens. x skal ligge mellem -1 og 1.\nEks: ArcTanh(0.5) ",
            "Cbrt": "Cbrt(x)\nKubikrod (tredje rod).\nEks: Cbrt(27) ",
            "Abs": "Abs(x)\nNumerisk værdi, altså afstanden til 0.\nEks: Abs(-5) ",
            "Floor": "Floor(x)\nRunder ned til nærmeste heltal.\nEks: Floor(2.7) ",
            "Ceil": "Ceil(x)\nRunder op til nærmeste heltal.\nEks: Ceil(2.1) ",
            "Round": "Round(x, decimaler)\nAfrunder til et antal decimaler. Decimaler er valgfrit.\nEks: Round(3.14159, 2) ",
            "Degrees": "Degrees(x)\nOmregner radianer til grader.\nEks: Degrees(3.14159) ",
            "Radians": "Radians(x)\nOmregner grader til radianer.\nEks: Radians(180) ",
            "Gamma": "Gamma(x)\nGammafunktionen. For heltal er Gamma(n) = (n-1)!\nEks: Gamma(5) ",
            "Erf": "Erf(x)\nFejlfunktionen (error function).\nEks: Erf(1) ",
        }

    input_prep = lambda self,x : quantity.si_convert(parser.evaluate(self.prep_ev(x)))

    def exclude_loops(self, lines):
        skip = []

        for n, line in enumerate(lines):
            line = re.sub(r"(\d)\s+\[", r"\1[", line)
            call = re.fullmatch(r"\s*(\w+)\((.*)\)\s*", line)
            if call and call.group(1) == "Loop":
                func, input = call.groups()
                try:
                    l1, l2, _ = (int(p) for p in input.split(","))
                except ValueError:
                    continue

                if not l1 - 1 <= n < l2:
                    skip.extend(range(l1 - 1, l2))

        return skip

    def split_args(self,input):
        args, depth, start = [], 0 ,0
        for i, char in enumerate(input):
            if char in "({":
                depth += 1
            elif char in ")}":
                depth -= 1

            elif char == "," and depth == 0:
                args.append(input[start:i])
                start = i + 1
        args.append(input[start:])

        return args

    equation_simlify = lambda x: simplify(parse_expr(x))

    def ev(self, s):
        output = {}

        lines = s.split("\n")

        skip = self.exclude_loops(lines)

        pc = 0
        while pc < len(lines):
            line = lines[pc]

            if "#" in line: line, _ = line.split("#",maxsplit=1)
                            

            if line.strip() == "" or pc in skip:
                pc += 1
                continue

            line = re.sub(r"(\d)\s+\[", r"\1[", line)

            
            
            try:
                call = re.fullmatch(r"\s*(\w+)\((.*)\)\s*", line)
                if call and call.group(1) in self.functions:
                    func, input = call.groups()
                    args = self.split_args(input)


                    match func:

                        case "Loop":
                            if len(args) != 3:
                                raise ValueError(self.error_text["Loop"])

                            l1, l2, count = args

                            if l1 == "" or l2 == "" or count == "":
                                raise ValueError(self.error_text["Loop"])

                            l1 = int(l1)
                            l2 = int(l2)
                            count = int(count)
                            if count > 10000: raise ValueError("Loop kan højst køre 10000 gange")


                            if l1 < 1 or l1 > l2 or l1 - 1 <= pc < l2:
                                raise ValueError("Kan ikke have loop inde i sig selv")

                            temp_interpreter = EV()
                            temp_interpreter.variables = dict(self.variables)
                            temp_lines = "\n".join(lines[l1 - 1 : l2])
                            results = []
                            for i in range(count):
                                temp_interpreter.variables["i"] = Variables(
                                    i, "quantity"
                                )
                                results += temp_interpreter.ev(temp_lines).values()
                                

                            self.variables = {
                                k: v
                                for k, v in temp_interpreter.variables.items()
                                if k != "i"
                            }
                            self._invalidate_pattern()

                            output[pc] = results

                            pc += 1

                        case 'Løs':
                            if len(args) not in (1, 2) or (len(args) == 2 and "Interval" not in args[1]):
                                raise ValueError(self.error_text["Løs"])
                            if "[" in args[0]:
                                raise ValueError("kan ikke tage imod enheder")

                            expr = self.prep_sympy(args[0])
                            f = expr.lhs - expr.rhs if isinstance(expr, sympy.Eq) else expr
                            if expr is sympy.true:
                                output[pc] = "Alle tal er løsninger"

                            elif len(args) == 2:
                                if len(f.free_symbols) != 1:
                                    raise ValueError(self.error_text["Løs"])
                                start,end = self.parse_interval(args[1], "Løs")
                                output[pc] = self.roots_in(f, f.free_symbols.pop(), start, end) or "Ingen løsninger i intervallet"

                            else:
                                try:
                                    solutions = [s for s in sympy.solve(self.prep_sympy(args[0]))]
                                except NotImplementedError:
                                    try:
                                        solutions = [self.clean_number(sympy.nsolve(f, 1))]
                                    except (ValueError, ZeroDivisionError):
                                        solutions = "Kunne ikke løses. Prøv med Interval = (start, slut)"
                                output[pc] = solutions if solutions else "Ingen løsninger"

                            pc += 1

                        case 'NumeriskLøs':
                            #Does not include system of equations
                            if len(args) < 2:
                                raise ValueError(self.error_text["NumeriskLøs"])
                            guess = 1
                            function = []
                            variabel = []
                            if any(part.strip() == "" for part in args):
                                raise ValueError(self.error_text["NumeriskLøs"])

                            

                            for part in args:
                                if "Variabel" in part:
                                    _,v = part.split("=")
                                    variabel.append(sympy.Symbol(v.strip()))
                    
                                elif "StartGæt" in part:
                                    _,g = part.split("=")
                                    guess = float(g)

                                else: function.append(self.prep_sympy(part))

                            if len(variabel) != 1 or len(function) != 1:
                                raise ValueError(self.error_text["NumeriskLøs"])
                            
                            output[pc] = sympy.nsolve(function[0],variabel[0],guess)
                            pc += 1

                        case 'SystemLøs':
                            functions = []
                            guess = None
                            interval = None
                            variables = None
                            if len(args) < 3:
                                raise ValueError(self.error_text["SystemLøs"])

                            for part in args:
                                if "Variabler" in part:
                                    _,v = part.split("=")
                                    if "(" not in v or ")" not in v:
                                        raise ValueError(self.error_text["SystemLøs"])
                                    variables = v.strip().strip("(").strip(")")
                                    variables = [sympy.Symbol(part.strip()) for part in variables.split(",")]

                                elif "StartGæt" in part:
                                    _,g = part.split("=")
                                    if "{" not in g or "}" not in g:
                                        raise ValueError(self.error_text["SystemLøs"])
                                    guess = [float(n) for n in g.strip().strip("{").strip("}").split(",")]

                                elif "Interval" in part:
                                    interval = self.parse_interval(part, "SystemLøs")

                                else: functions.append(self.prep_sympy(part))

                            if variables == None:
                                raise ValueError(self.error_text["SystemLøs"])
                            
                            guess = guess or [1] * len(variables)
                            if len(guess) != len(variables):
                                raise ValueError(self.error_text["SystemLøs"])

                            if interval:
                                result = self.system_roots_in(functions, variables, *interval) or "Ingen løsninger i intervallet"
                            else:
                                pool = ThreadPool(1)
                                task = pool.apply_async(sympy.solve, (functions, *variables), {"dict": True})
                                pool.close()
                                try:
                                    result = task.get(timeout = 20)
                                except (multiprocessing.TimeoutError, NotImplementedError):
                                    try:
                                        result = [{k: self.clean_number(v) for k, v in sympy.nsolve(functions, variables, guess, dict = True)[0].items()}]
                                    except (ValueError, ZeroDivisionError):
                                        result = "Kunne ikke løses. Prøv et andet StartGæt"

                            output[pc] = result or "Ingen løsninger"

                            pc+=1

                        case 'Simplificer':
                            if len(args) != 1:
                                raise ValueError(self.error_text["Simplificer"])
                            output[pc] = sympy.N(simplify(self.prep_sympy(args[0])))
                            pc +=1

                        case 'PlotFunktion':
                            start = None
                            end = None
                            functions = []

                            for part in args:
                                if "Interval" in part:
                                    _,interval = part.split("=")
                                    if "(" not in interval or ")" not in interval:
                                        raise ValueError(self.error_text["PlotFunktion"])
                                    interval = interval.strip().strip("(").strip(")")

                                    if interval.count(",") != 1:
                                        raise ValueError(self.error_text["PlotFunktion"])
                                    start,end = interval.split(",")
                                    if start == "" or end == "":
                                        raise ValueError(self.error_text["PlotFunktion"])
                                    start = self.input_prep(start).value
                                    end = self.input_prep(end).value
                                else: 
                                    functions.append(self.prep_sympy(part))
                            if start is not None:
                                 output[pc] = utils.FunctionPlot(functions,start,end)
                            else:
                                output[pc] = utils.FunctionPlot(functions)
                            pc += 1

                        case 'Regression':
                            if len(args) != 3:
                                raise ValueError(self.error_text["Regression"])
                            xs = [float(part) for part in self.prep_ev(args[1]).strip().strip("{}").split(",")]
                            ys = [float(part) for part in self.prep_ev(args[2]).strip().strip("{}").split(",")]
                            if len(xs) != len(ys):
                                raise ValueError("ikke lige mange x og y værdier")
                            
                            expr = self.prep_sympy(args[0])
                            x = sympy.Symbol("x")
                            params = sorted(expr.free_symbols - {x}, key=str)
                            f = sympy.lambdify((x, *params), expr, "numpy")

                            output[pc] = utils.regretion(f,expr,params,xs,ys)
                            pc+=1

                        case 'LinReg':
                            if len(args) != 2:
                                raise ValueError(self.error_text["LinReg"])
                            xs = [float(part) for part in self.prep_ev(args[0]).strip().strip("{}").split(",")]
                            ys = [float(part) for part in self.prep_ev(args[1]).strip().strip("{}").split(",")]

                            expr = self.prep_sympy("ax + b")
                            x = sympy.Symbol("x")
                            params = sorted(expr.free_symbols - {x}, key=str)

                            f = sympy.lambdify((x, *params), expr, "numpy")

                            output[pc] = utils.regretion(f,expr,params,xs,ys)
                            pc += 1

                        case 'PropReg':
                            if len(args) != 2:
                                raise ValueError(self.error_text["PropReg"])
                            xs = [float(part) for part in self.prep_ev(args[0]).strip().strip("{}").split(",")]
                            ys = [float(part) for part in self.prep_ev(args[1]).strip().strip("{}").split(",")]

                            expr = self.prep_sympy("ax")
                            x = sympy.Symbol("x")
                            params = sorted(expr.free_symbols - {x}, key=str)

                            f = sympy.lambdify((x, *params), expr, "numpy")

                            output[pc] = utils.regretion(f,expr,params,xs,ys)
                            pc += 1

                        case 'ExpReg':
                            if len(args) != 2:
                                raise ValueError(self.error_text["ExpReg"])
                            xs = [float(part) for part in self.prep_ev(args[0]).strip().strip("{}").split(",")]
                            ys = [float(part) for part in self.prep_ev(args[1]).strip().strip("{}").split(",")]

                            expr = self.prep_sympy("a*b^x")
                            x = sympy.Symbol("x")
                            params = sorted(expr.free_symbols - {x}, key=str)

                            f = sympy.lambdify((x, *params), expr, "numpy")

                            output[pc] = utils.regretion(f,expr,params,xs,ys)
                            pc += 1

                        case 'KvadReg':
                            if len(args) != 2:
                                raise ValueError(self.error_text["KvadReg"])
                            xs = [float(part) for part in self.prep_ev(args[0]).strip().strip("{}").split(",")]
                            ys = [float(part) for part in self.prep_ev(args[1]).strip().strip("{}").split(",")]

                            expr = self.prep_sympy("a*x^2 + bx + c")
                            x = sympy.Symbol("x")
                            params = sorted(expr.free_symbols - {x}, key=str)

                            f = sympy.lambdify((x, *params), expr, "numpy")

                            output[pc] = utils.regretion(f,expr,params,xs,ys)
                            pc += 1

                        case 'LogistReg':
                            if len(args) != 2:
                                raise ValueError(self.error_text["LogistReg"])
                            xs = [float(part) for part in self.prep_ev(args[0]).strip().strip("{}").split(",")]
                            ys = [float(part) for part in self.prep_ev(args[1]).strip().strip("{}").split(",")]

                            expr = self.prep_sympy("c/(1+aE^(-bx))")
                            x = sympy.Symbol("x")
                            params = sorted(expr.free_symbols - {x}, key=str)

                            f = sympy.lambdify((x, *params), expr, "numpy")

                            output[pc] = utils.regretion(f,expr,params,xs,ys)
                            pc += 1 

                        case 'HarmReg':
                            if len(args) != 2:
                                raise ValueError(self.error_text["HarmReg"])
                            xs = [float(part) for part in self.prep_ev(args[0]).strip().strip("{}").split(",")]
                            ys = [float(part) for part in self.prep_ev(args[1]).strip().strip("{}").split(",")]

                            expr = self.prep_sympy("a*sin(b*x+c)+d")
                            x = sympy.Symbol("x")
                            params = sorted(expr.free_symbols - {x}, key=str)

                            f = sympy.lambdify((x, *params), expr, "numpy")

                            output[pc] = utils.regretion(f,expr,params,xs,ys)
                            pc += 1  

                                              









                        case 'Afstem':
                            if len(args) > 2:
                                raise ValueError(self.error_text["Afstem"])
                            if len(args) == 2:
                                input, medium = args
                                if input == "" or medium == "":
                                    raise ValueError(self.error_text["Afstem"])
                                result = chem.balance_reaction(input, medium)
                            else:
                                result = chem.balance_reaction(input)

                            output[pc] = result
                            pc += 1

                        case "pH":
                            if len(args) != 2:
                                raise ValueError(self.error_text["pH"])
                            x, c = (p.strip() for p in args)
                            if x == "" or c == "":
                                raise ValueError(self.error_text["pH"])

                            

                            q = parser.evaluate(self.prep_ev(c))
                            con = q.value if not q.dimension else quantity.unit_convert(q, "mol/l").value
                            result = chem.pH(x, con)
                            result = utils.round_pH(result, [self.prep_ev(c)])
                            output[pc] = result
                            pc += 1

                        case "pOH":
                            if len(args) != 2:
                                raise ValueError(self.error_text["pOH"])
                            x, c = (p.strip() for p in args)
                            if x == "" or c == "":
                                raise ValueError(self.error_text["pOH"])

                            q = parser.evaluate(self.prep_ev(c))
                            con = q.value if not q.dimension else quantity.unit_convert(q, "mol/l").value
                            result = chem.pOH(x, con)
                            result = utils.round_pH(result, [self.prep_ev(c)])
                            output[pc] = result
                            pc += 1

                        case "EnhedKonvertering":
                            if len(args) != 2:
                                raise ValueError(self.error_text["EnhedKonvertering"])
                            start, unit = args
                            if start == "" or unit == "":
                                raise ValueError(self.error_text["EnhedKonvertering"])
                            Qstart = self.input_prep(start)
                     
                  
                        
                            unit = unit.strip()
                            if unit.lower() == "si":
                                result = quantity.si_convert(Qstart)
                            else:
                                result = quantity.unit_convert(Qstart, unit)

                            output_unit = result.current_units
                            
                            output[pc] = round_quantity(result,[self.prep_ev(start)])
                            pc += 1

                        case "Analyse":
                            if len(args) != 1:
                                raise ValueError(self.error_text["Analyse"])
                            if input == "":
                                raise ValueError(self.error_text["Analyse"])
                            molecule, emp, mol, count, procent, dbe = (
                                chem.elemental_analasis(input)
                            )
                            indhold = f"Masseprocent:\n{'\n'.join(procent)}"
                            output[pc] = (
                                f"Molekyle: {molecule}\nEmpirisk formel: {emp}\nMolar masse: {quantity.create_quantity(round(mol,config.rounding_decimals),"g/mol")}\nDBE: {dbe} \nAntal atomer: {count} \n{indhold}"
                            )
                            pc += 1

                        case "BjerrumDiagram":
                            inline = True
                            if input == "":
                                raise ValueError(self.error_text["BjerrumDiagram"])
                            pks_values = []


                            for part in args:
                                value = chem.find_pk(pKa_values, part)
                                if value is not None:
                                    pks_values.append(value)
                                elif "export" in part.lower():
                                    inline = False
                                else:
                                    pks_values.append(self.input_prep(part).value)

                            if len(pks_values) == 0:
                                raise ValueError(f"ingen pKs-værdier: {self.error_text["BjerrumDiagram"]}")

                            pks_values = [float(x) for x in pks_values]

                            if inline:
                                output[pc] = chem.bjerrum_figure(pks_values)

                            else: chem.bjerrum(pks_values)
                            pc += 1

                        case (
                            "UdbytteProcent"
                            | "VolumenProcent"
                            | "MasseProcent" as procent_type
                        ):
                            if len(args) != 2:
                                raise ValueError(self.error_text[procent_type])
                            top, bottom = args
                            if top == "" or bottom == "":
                                raise ValueError(self.error_text[procent_type])


                            top_preped = self.input_prep(top)
                            bottom_preped = self.input_prep(bottom)

                            result = chem.procent(top_preped, bottom_preped)
                            
                          
                            output[pc] = f'{round_quantity(result,[self.prep_ev(top),self.prep_ev(bottom)])}%'
                            pc += 1

                        case 'DNATilPeptid':
                            if len(args) != 1:
                                raise ValueError(self.error_text["DNATilPeptid"])
                            if input == "":
                                raise ValueError(self.error_text["DNATilPeptid"])

                            output[pc] = biotek.DNA_to_peptide(input)
                            pc +=1
                                
                        case 'RNATilPeptid':
                            if len(args) != 1:
                                raise ValueError(self.error_text["RNATilPeptid"])
                            if input == "":
                                raise ValueError(self.error_text["RNATilPeptid"])

                            output[pc] = biotek.RNA_to_peptide(input)
                            pc +=1

                        case "MængdeBeregning":
                            if len(args) > 6:
                                raise ValueError(self.error_text["MængdeBeregning"])

                            if input == "":   
                                raise ValueError(self.error_text["MængdeBeregning"])
                           
                            tokens = args


                            if  "" in tokens:
                                raise ValueError(self.error_text["MængdeBeregning"])

                            if len(tokens) == 1:
                                raise ValueError(self.error_text["MængdeBeregning"])
    
                            tokens = [token.strip() for token in tokens]

                            

                            key_map = {
                                "m": "Masse", "V": "Volumen", "n": "Stofmængde",
                                "c": "Koncentration", "M": "Molarmasse", "p": "Densitet",
                            }
                            unit_map = {
                                "m": "g", "V": "l", "n": "mol",
                                "c": "mol/l", "M": "g/mol", "p": "kg/l",
                            }
                            unit_map2 = {v: unit_map[k] for k, v in key_map.items()}
                            short_key_map = {v: k for k, v in key_map.items()}
    
                            
                            relations = [("m", "n", "M"), ("n", "c", "V"), ("m", "p", "V")]
    
                            kwargs = {}
                            raw_values = {}     
                            provided_keys = set()
    
                            for token in tokens:
                                if "=" not in token:
                                    raise ValueError(self.error_text["MængdeBeregning"])
                                key, val = token.split("=", maxsplit=1)
                                key = key.strip()
                                if key not in key_map:
                                    raise ValueError(f"Ukendt input {key!r}")
    
                                raw_values[key] = self.prep_ev(val)
    
                                provided_keys.add(key)

                                q = parser.evaluate(self.prep_ev(val))
                                if not q.dimension:
                                    q = quantity.create_quantity(q.value,unit_map[key])
                                kwargs[key_map[key]] = quantity.si_convert(q)
                                
                            result = chem.mængdeberegning(**kwargs)
    
                            def find_deps(unknown):  
                                for trio in relations:
                                    if unknown in trio:
                                        others = [x for x in trio if x != unknown]
                                        if all(o in provided_keys for o in others):
                                            return others
                        
                                return list(provided_keys)
    
                            linjer = []
                            for k, v in result.items():
                                if v is None:
                                    continue
    
                                short = short_key_map[k]
                                converted = quantity.unit_convert(v, unit_map2[k])   
    
                                if short in provided_keys:
                                    val = converted.value
                                    if isinstance(val, float) and val.is_integer():
                                        val = int(val)
                                    linjer.append(f"{k}: {quantity(val, converted.dimension, converted.current_units)}")
                                else:
                                    sig_inputs = [raw_values[d] for d in find_deps(short)]
                                    rounded = utils.significant_figures(converted.value, sig_inputs) 
                                    linjer.append(f"{k}: {quantity(rounded, converted.dimension, converted.current_units)}")
    
                            output[pc] = "\n".join(linjer) if linjer else ""
                            pc += 1


                        case 'Puffer':   
                            if len(args) != 3:
                                raise ValueError(self.error_text["Puffer"])
                            syre, base, pKs = args

                            if syre == "" or base == "" or pKs == "": 
                                raise ValueError(self.error_text["Puffer"])

                            result = chem.puffer(self.input_prep(syre).value,self.input_prep(base).value,self.input_prep(pKs).value)                   
                            output[pc] = utils.round_pH(result,[self.prep_ev(syre),self.prep_ev(base)])

                            pc += 1

                        case 'pHTilKoncentration':
                            if len(args) != 1:
                                raise ValueError(self.error_text["pHTilKoncentration"])

                            if input == "":
                                raise ValueError(self.error_text["pHTilKoncentration"])

                            h3o, oh = chem.pH_to_concentration(self.input_prep(input).value)
                            sig = [self.prep_ev(input)]
                            output[pc] = f"[H3O+]: {utils.significant_figures(h3o, sig)} mol/l\n[OH-]: {utils.significant_figures(oh, sig)} mol/l"

                            pc += 1

                

                        case "Help":
                            if input == "":
                                output[pc] = "\n".join(self.functions)
                            else:
                                if input not in self.help_text:
                                    raise ValueError(
                                        f"Ukendt funktion {input}, eller ingen hjælpetext til funktionen"
                                    )
                                output[pc] = self.help_text[input]

                            pc += 1

                        

                else:
                    try:
                        if "+=" in line:
                            a, b = (p.strip() for p in line.split("+=", 1))
                            if a not in self.variables:
                                raise ValueError(f'Ukendt variabel {a}')

                            self.variables[a] = Variables(
                                quantity.simplify_units(parser.evaluate(self.prep_ev(f"{a}+({b})"))), "Quantity"
                            )
                            output[pc] = self.variables[a].value
                            pc +=1

                        elif "-=" in line:
                            a, b = (p.strip() for p in line.split("-=", 1))
                            if a not in self.variables:
                                raise ValueError(f'Ukendt variabel {a}')

                            self.variables[a] = Variables(
                                quantity.simplify_units(parser.evaluate(self.prep_ev(f"{a}-({b})"))), "Quantity"
                            )
                            output[pc] = self.variables[a].value
                            pc +=1

                        elif "=" in line:
                            a, b = (p.strip() for p in line.split("=", 1))
                            if a == "" or b == "":
                                raise ValueError("Variabel er defineret forkert")
                            if not re.fullmatch(r"[^\W\d]\w*", a) or a in self.functions or a in SYMPY_FUNCTIONS or a in CONSTANTS:
                                raise ValueError(f"{a} kan ikke bruges som variabelnavn")

                            if '"' in b or "'" in b:
                                if "'" in b and '"' in b:
                                    raise ValueError(
                                        "Man kan ikke både bruge ' og " + '"'
                                    )
                                elif "'" in b:
                                    if b.count("'") != 2:
                                        raise ValueError(
                                            "Du skal slutte og starte din tekst med enten: '  eller "
                                            + '"'
                                        )

                                elif '"' in b:
                                    if b.count('"') != 2:
                                        raise ValueError(
                                            "Du skal slutte og starte din tekst med enten: '  eller "
                                            + '"'
                                        )

                                self.variables[a] = Variables(
                                    b.strip("'").strip('"'), "str"
                                )

                            elif '{' in b or '}' in b:
                                if '{' not in b or not '}' in b:
                                    raise ValueError("Du skal slutte og starte en liste med { og }")

                               
                                self.variables[a] = Variables(b,"list")


                            else:
                                self.variables[a] = Variables(
                                    quantity.simplify_units(parser.evaluate(self.prep_ev(b))), "Quantity"
                                )
                            self._invalidate_pattern()
                            output[pc] = self.variables[a].value
                            pc += 1
       
                        elif re.search(r"(?<![A-Za-z])(integrate|diff|limit|summation)\(", line):
                            output[pc] = safe_parse(line, {**SYMPY_FUNCTIONS, "e": sympy.E, "π": sympy.pi})
                            pc += 1

                        else:
                            output[pc] = quantity.simplify_units(parser.evaluate(self.prep_ev(line)))
                            pc += 1
                    except Exception as e:
                        raise ValueError(e)

            except Exception as e:
                output[pc] = f"Error: {e}"
                pc += 1
        return output

    def _invalidate_pattern(self):
        self._pattern_dirty = True

    def _get_pattern(self):
        if self._pattern_dirty:
            if self.variables:
                names = sorted(self.variables, key=len, reverse=True)
                self._pattern = re.compile(
                    r"(?<![A-Za-zæøåÆØÅ_])(" + "|".join(re.escape(n) for n in names) + r")(?!\w)"
                )
            else:
                self._pattern = None
            self._pattern_dirty = False
        return self._pattern

    def prep_ev(self, expr):
        expr = str(expr)
        pattern = self._get_pattern()
        if pattern:
            parts = re.split(r"(\[[^\]]*\])", expr)  # bracket parts land on odd indexes
            for i in range(0, len(parts), 2):
                parts[i] = pattern.sub(
                    lambda m: "(" + self.variables[m.group(0)].value + ")"
                    if self.variables[m.group(0)].var_type.lower() == "quantity"
                    else self.variables[m.group(0)].value,
                    parts[i],
                )
            expr = "".join(parts)
        expr = re.sub(r"\[([^\]]*)\]", r" (\1)", expr)
        return expr
    
    def prep_sympy(self, expr):
        if "=" in expr:
            lhs, rhs = expr.split("=",maxsplit = 1)
            return sympy.Eq(safe_parse(lhs, SYMPY_FUNCTIONS), safe_parse(rhs, SYMPY_FUNCTIONS))
        return safe_parse(expr, SYMPY_FUNCTIONS)
    
    def parse_interval(self, part, name):
        _,interval = part.split("=")
        if "(" not in interval or ")" not in interval or interval.count(",") != 1:
            raise ValueError(self.error_text[name])
        start,end = interval.strip().strip("(").strip(")").split(",")
        if start.strip() == "" or end.strip() == "":
            raise ValueError(self.error_text[name])
        start,end = self.input_prep(start).value, self.input_prep(end).value
        if start >= end:
            raise ValueError(self.error_text[name])
        return start, end

    def clean_number(self, value):
        return sympy.Float(round(float(value), 12) + 0.0)

    def roots_in(self, expr, var, start, end):
        f = sympy.lambdify(var, expr, "numpy")
        xs = np.linspace(start, end, 2001)
        with np.errstate(all = "ignore"):
            ys = np.broadcast_to(f(xs), xs.shape)
        zero = lambda y: np.isfinite(y) and abs(y) < 1e-12
        roots = [x for x, y in zip(xs, ys) if zero(y)]
        for a, b, fa, fb in zip(xs, xs[1:], ys, ys[1:]):
            if not (np.isfinite(fa) and np.isfinite(fb)) or zero(fa) or zero(fb) or fa * fb > 0:
                continue
            try:
                r = float(sympy.nsolve(expr, var, (a, b), solver = "bisect", verify = False))
            except (ValueError, ZeroDivisionError):
                continue
            with np.errstate(all = "ignore"):
                if abs(f(r)) < 1e-6 * max(abs(fa), abs(fb)):
                    roots.append(r)
        return sorted({self.clean_number(r) for r in roots})

    def system_roots_in(self, functions, variables, start, end):
        first, rest = variables[0], variables[1:]
        for i, last in enumerate(functions):
            try:
                branches = sympy.solve(functions[:i] + functions[i + 1:], rest, dict = True)
            except NotImplementedError:
                continue
            branches = [b for b in branches if set(b) == set(rest)]
            if not branches:
                continue
            found = []
            for branch in branches:
                eq = last.subs(branch)
                if first not in eq.free_symbols:
                    continue
                f = eq.lhs - eq.rhs if isinstance(eq, sympy.Eq) else eq
                for r in self.roots_in(f, first, start, end):
                    values = {v: e.subs(first, r).evalf() for v, e in branch.items()}
                    if not all(val.is_real for val in values.values()):
                        continue
                    solution = {first: r, **{v: self.clean_number(val) for v, val in values.items()}}
                    if solution not in found:
                        found.append(solution)
            return sorted(found, key = lambda s: s[first])
        raise ValueError("Kan ikke søge i et interval her. Brug StartGæt i stedet")

    def unit_bracket_strip(self, val):
        match = re.match(r"([^\[]+)\[([^\]]+)\]", val)
        if not match:
            raise ValueError(f"Kunne ikke læse værdi/enhed: {val!r}")

        num_str, unit = match.group(1), match.group(2)

        if "," in num_str:
            raise ValueError("Brug punktum som decimal tal ikke komma")

        value = float(num_str)

        return value, unit
