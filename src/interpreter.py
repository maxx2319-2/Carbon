import parser
import utils
import chem
from quantity import quantity
import re
import biotek
import json
import sympy 
from sympy import symbols, simplify,sin, cos
import numpy as np
from matplotlib.figure import Figure
from sympy.parsing.sympy_parser import parse_expr, standard_transformations, implicit_multiplication, convert_xor, split_symbols

from types import SimpleNamespace
from chem import pKa_values,pKb_values

from path import resource_path
from pathlib import Path



with open(resource_path("config.json")) as f:
    config = json.load(f, object_hook=lambda d: SimpleNamespace(**d))


def as_expr(q):
    parts = [repr(q.value)] + [f"{u}^({p})" for u, p in q.units.items()]
    return "(" + "*".join(parts) + ")"


def round_quantity(quant,inputs):
    value = utils.significant_figures(quant.value,inputs)
    return quantity(value,quant.units)


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
}


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
            "PlotFunktion",
            "NumeriskLøs",
            "SystemLøs",
            "Simplificer",

        ]

        self.error_text = {
            "Help" : "Help() or Help(function)",
            "Afstem": "Afstem(reaktion,opløsning(syre,base eller ingenting))",
            "pH": "pH(pKs eller syre/base navn,Koncentration)",
            "pOH": "pOH(pBs eller syre/base navn,Koncentration)",
            "EnhedKonvertering": 'EnhedKonvertering(Quantity,ny Enhed eller "SI" for SI enhed)',
            "Loop": "Loop(start linje,slut linje,antal gange)",
            "Analyse": "Analyse(molekyle)",
            "BjerrumDiagram": "Bjerrumdiagram(pKs1,pKs2,...)",
            "UdbytteProcent":"UdbytteProcent(Praktisk,Teoretisk)" ,
            "VolumenProcent":"VolumenProcent(Praktisk,Teoretisk)",
            "MasseProcent":"MasseProcent(Praktisk,Teoretisk)",
            "DNATilPeptid":"DNATilPeptid(DNA streng)",
            "RNATilPeptid":"RNATilPeptid(DNA streng)",
            "MængdeBeregning": "MængdeBeregning(m=..,n=..,etc)",
            "Puffer" : "Puffer(Syre concentration,Base concentration, pKs)",
            "pHTilKoncentration" : "pHTilKoncentration(pH)",
            "Løs" : "Løs(ligning)",
            "PlotFunktion" : "PlotFunktion(function 1,function 2,...,Interval = (x start , x slut) )",
            "NumeriskLøs" : "NumeriskLøs(function, variabel, evt gæt)",
            "SystemLøs" : "SystemLøs(ligning 1,ligning 2,ligning... , Variabler = {x, y, ...})",
            "Simplificer" : "Simplificer(x)",
        }

        self.help_text = {
            "Help": "Help() eller Help(funktion)\nViser alle funktioner, eller hjælp til én funktion.\nEks: Help(pH) ",
            "Afstem": "Afstem(reaktion, opløsning)\nAfstemmer en reaktion. Opløsning er syre, base eller udeladt.\nEks: Afstem(H2 + O2 -> H2O) ",
            "pH": "pH(pKs eller syre navn eller base navm, koncentration)\nBeregner pH for en syre eller base.\nEks: pH(4.76, 0.10) ",
            "pOH": "pOH(pKb eller base navn eller syre navn, koncentration)\nBeregner pOH for en base eller syre.\nEks: pOH(4.75, 0.10) ",
            "EnhedKonvertering": 'EnhedKonvertering(størrelse, ny enhed eller "SI")\nKonverterer en størrelse til en ny enhed eller til SI enhed.\nEks: EnhedKonvertering(4[km],SI) ',
            "Loop": "Loop(start linje, slut linje, antal gange)\nKører linjerne fra start til slut flere gange. Variablen i tæller fra 0.\nEks: Loop(1, 3, 5) ",
            "Analyse": "Analyse(molekyle)\nViser empirisk formel, molar masse, DBE, antal atomer og masseprocent.\nEks: Analyse(C6H12O6) ",
            "BjerrumDiagram": "BjerrumDiagram(pKs1, pKs2, ..., export)\nTegner et Bjerrumdiagram ud fra pKs værdier eller syre navne. Skriv export for at åbne det i et nyt vindue.\nEks: BjerrumDiagram(2.15, 7.20, 12.35) ",
            "UdbytteProcent": "UdbytteProcent(praktisk, teoretisk)\nBeregner udbyttet i procent.\nEks: UdbytteProcent(4.5[g], 5[g]) ",
            "VolumenProcent": "VolumenProcent(praktisk, teoretisk)\nBeregner volumenprocent.\nEks: VolumenProcent(40[ml], 100[ml]) ",
            "MasseProcent": "MasseProcent(praktisk, teoretisk)\nBeregner masseprocent.\nEks: MasseProcent(12[g], 50[g]) ",
            "DNATilPeptid": "DNATilPeptid(DNA streng)\nOversætter en DNA streng til et peptid.\nEks: DNATilPeptid(ATGGCCTAA) ",
            "RNATilPeptid": "RNATilPeptid(RNA streng)\nOversætter en RNA streng til et peptid.\nEks: RNATilPeptid(AUGGCCUAA) ",
            "MængdeBeregning": "MængdeBeregning(m=.., n=.., ...)\nBeregner de manglende størrelser ud fra m, n, M, c, V og p .\nEks: MængdeBeregning(m=10[g], M=58.44[g/mol], V=0.5[l]) ",
            "Puffer": "Puffer(syre koncentration, base koncentration, pKs)\nBeregner pH i en puffer med pufferligningen.\nEks: Puffer(0.10, 0.10, 4.76) ",
            "pHTilKoncentration": "pHTilKoncentration(pH)\nBeregner [H3O+] og [OH-] ud fra pH.\nEks: pHTilKoncentration(3.5) ",
            "Løs": "Løs(ligning)\nLøser en ligning. Kan ikke tage imod enheder.\nEks: Løs(x^2 = 4) ",
            "PlotFunktion": "PlotFunktion(funktion 1, funktion 2, ..., Interval = (x start, x slut))\nTegner en eller flere funktioner. Interval er valgfrit.\nEks: PlotFunktion(x^2, Sin(x), Interval=(-5,5)) ",
            "NumeriskLøs": "NumeriskLøs(funktion, Variabel = x, StartGæt = 1)\nLøser en ligning numerisk ud fra et startgæt. StartGæt er valgfrit.\nEks: NumeriskLøs(Cos(x) = x, Variabel = x, StartGæt = 10) ",
            "SystemLøs": "SystemLøs(ligning 1, ligning 2, ..., Variabler = {x, y, ...})\nLøser et ligningssystem med flere ubekendte.\nEks: SystemLøs(x + y = 10, x - y = 2, Variabler = {x, y}) ",
            "Simplificer": "Simplificer(udtryk)\nUdregner et udtryk med kvadratrødder, brøker osv. til et decimaltal.\nEks: Simplificer(sqrt(12) + sqrt(27)) ",
        }

    input_prep = lambda self,x : quantity.si_convert(parser.evaluate(self.prep_ev(x)))

    def exclude_loops(self, lines):
        skip = []

        for n, line in enumerate(lines):
            line = re.sub(r"(\d)\s+\[", r"\1[", line)
            call = re.fullmatch(r"\s*(\w+)\((.*)\)\s*", line)
            if call and call.group(1) == "loop":
                func, input = call.groups()
                if func == "Loop":

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

        lines = s.splitlines()

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
                            if len(args) != 1:
                                raise ValueError(self.error_text["Løs"])
                            if "[" in args[0]:
                                raise ValueError("kan ikke tage imod enheder")

                            expr = self.prep_sympy(args[0])
                            if expr is sympy.true:
                                output[pc] = "Alle tal er løsninger"

                            else:
                                solutions = [s for s in sympy.solve(self.prep_sympy(args[0]))]
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
                            if len(args) < 3:
                                raise ValueError(self.error_text["SystemLøs"])

                            for part in args:
                                if "Variabler" in part:
                                    _,v = part.split("=")
                                    if "{" not in v or "}" not in v:
                                        raise ValueError(self.error_text["SystemLøs"])
                                    variables = v.strip().strip("{").strip("}")
                                    variables = [sympy.Symbol(part.strip()) for part in variables.split(",")]

                                else: functions.append(self.prep_sympy(part))

                            result = sympy.solve(functions,*variables,dict = True)
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

                            

                            result = chem.pH(x, self.input_prep(c).value)
                            result = utils.round_pH(result, [self.prep_ev(c)])
                            output[pc] = result
                            pc += 1

                        case "pOH":
                            if len(args) != 2:
                                raise ValueError(self.error_text["pOH"])
                            x, c = (p.strip() for p in args)
                            if x == "" or c == "":
                                raise ValueError(self.error_text["pOH"])

                            result = chem.pOH(x, self.input_prep(c).value)
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

                            output_unit = result.units
                            
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
                            indhold = f"Masse procent:\n{'\n'.join(procent)}"
                            output[pc] = (
                                f"Molekyle: {molecule}\nEmpirisk formel: {emp}\nMolar masse: {round(mol,config.rounding_decimals)}\nDBE: {dbe} \nAntal atomer: {count} \n{indhold}"
                            )
                            pc += 1

                        case "BjerrumDiagram":
                            inline = True
                            if input == "":
                                raise ValueError(self.error_text["BjerrumDiagram"])
                            pks_values = []


                            for part in args:
                                if part in pKa_values:
                                    pks_values.append(pKa_values[part])
                                elif "export" in part.lower():
                                    inline = False
                                else:
                                    pks_values.append(self.input_prep(part).value)

                            if len(pks_values) == 0:
                                raise ValueError(f"ingen pKs værdier: {self.error_text["BjerrumDiagram"]}")

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
                                if key not in key_map:
                                    raise ValueError(f"Ukendt input {key!r}")
    
                                raw_values[key] = val
    
                                provided_keys.add(key)
    
                                if "[" not in val:
                                    val = f'{val}[{unit_map[key]}]'
                                v, u = self.unit_bracket_strip(val)
                                kwargs[key_map[key]] = quantity.si_convert(quantity.quantity_convert(v, u))
    
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
                                    linjer.append(f"{k}: {quantity(val, converted.units)}")
                                else:
                                    sig_inputs = [raw_values[d] for d in find_deps(short)]
                                    rounded = utils.significant_figures(converted.value, sig_inputs) 
                                    linjer.append(f"{k}: {quantity(rounded, converted.units)}")
    
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
                                if input not in self.error_text:
                                    raise ValueError(
                                        f"Ukendt function {input}, eller ingen hjælpe text til functionen"
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
                                parser.evaluate(self.prep_ev(f"{a}+({b})")), "Quantity"
                            )
                            output[pc] = self.variables[a].value
                            pc +=1

                        elif "-=" in line:
                            a, b = (p.strip() for p in line.split("-=", 1))
                            if a not in self.variables:
                                raise ValueError(f'Ukendt variabel {a}')

                            self.variables[a] = Variables(
                                parser.evaluate(self.prep_ev(f"{a}-({b})")), "Quantity"
                            )
                            output[pc] = self.variables[a].value
                            pc +=1

                        elif "=" in line:
                            a, b = (p.strip() for p in line.split("=", 1))
                            if a == "" or b == "":
                                raise ValueError("Variabel er defineret forkert")
                            if '"' in b or "'" in b:
                                if "'" in b and '"' in b:
                                    raise ValueError(
                                        "Man kan ikke både bruge ' og " + '"'
                                    )
                                elif "'" in b:
                                    if b.count("'") != 2:
                                        raise ValueError(
                                            "Du skal slutte og starte din text med enten: '  eller "
                                            + '"'
                                        )

                                elif '"' in b:
                                    if b.count('"') != 2:
                                        raise ValueError(
                                            "Du skal slutte og starte din text med enten: '  eller "
                                            + '"'
                                        )

                                self.variables[a] = Variables(
                                    b.strip("'").strip('"'), "str"
                                )

                            elif '{' in b or '}' in b:
                                if '{' not in b or not '}' in b:
                                    raise ValueError("Du skal slutte og starte en liste med { og }")

                                b = b.strip("{").strip("}")
                                b = b.split(",")
                                self.variables[a] = Variables(b,"list")


                            else:
                                self.variables[a] = Variables(
                                    parser.evaluate(self.prep_ev(b)), "Quantity"
                                )
                            self._invalidate_pattern()
                            output[pc] = self.variables[a].value
                            pc += 1





                        else:
                            output[pc] = parser.evaluate(self.prep_ev(line))
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
                    r"\b(" + "|".join(re.escape(n) for n in names) + r")\b"
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
                    lambda m: self.variables[m.group(0)].value, parts[i]
                )
            expr = "".join(parts)
        expr = re.sub(r"\[([^\]]*)\]", r" (\1)", expr)
        return expr

    def prep_sympy(self, expr):
        transformations = standard_transformations + (split_symbols, implicit_multiplication, convert_xor)
        if "=" in expr:
            lhs, rhs = expr.split("=",maxsplit = 1)
            return sympy.Eq(parse_expr(lhs, transformations=transformations, local_dict=SYMPY_FUNCTIONS),parse_expr(rhs, transformations=transformations, local_dict=SYMPY_FUNCTIONS))
        return parse_expr(expr, transformations=transformations, local_dict=SYMPY_FUNCTIONS)

    def unit_bracket_strip(self, val):
        match = re.match(r"([^\[]+)\[([^\]]+)\]", val)
        if not match:
            raise ValueError(f"could not parse value/unit: {val!r}")

        num_str, unit = match.group(1), match.group(2)

        if "," in num_str:
            raise ValueError("Brug punktum som decimal tal ikke komma")

        value = float(num_str)

        return value, unit
