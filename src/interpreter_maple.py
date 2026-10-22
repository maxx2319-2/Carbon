import parser
import utils
import chem
from quantity import quantity
import re
import biotek
import json
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
    input_values = [float(part.split()[0]) for part in inputs]
    value = utils.significant_figures(quant.value,input_values)
    return quantity(value,quant.units)


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
            "UdbytteProcent":"UdbytteProcent(Tæller,Nævner)" ,
            "VolumenProcent":"VolumenProcent(Tæller,Nævner)",
            "MasseProcent":"MasseProcent(Tæller,Nævner)",
            "DNATilPeptid":"DNATilPeptid(DNA streng)",
            "RNATilPeptid":"RNATilPeptid(DNA streng)",
            "MængdeBeregning": "MængdeBeregning(m=..,n=..,etc)"

        }
        # temp fix
        self.help_text = self.error_text

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

                    match func:

                        case "Loop":
                            if line.count(",") != 2:
                                raise ValueError(self.error_text["Loop"])

                            l1, l2, count = input.split(",")

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

                        case "Afstem":
                            if line.count(",") > 1:
                                raise ValueError(self.error_text["Afstem"])
                            if "," in input:
                                input, medium = input.split(",")
                                if input == "" or medium == "":
                                    raise ValueError(self.error_text["Afstem"])
                                result = chem.balance_reaction(input, medium)
                            else:
                                result = chem.balance_reaction(input)

                            output[pc] = result
                            pc += 1

                        case "pH":
                            if line.count(",") != 1:
                                raise ValueError(self.error_text["pH"])
                            x, c = (p.strip() for p in input.split(","))
                            if x == "" or c == "":
                                raise ValueError(self.error_text["pH"])

                            

                            result = chem.pH(x, self.input_prep(c).value)
                            result = utils.round_pH(result, [self.prep_ev(c)])
                            output[pc] = result
                            pc += 1

                        case "pOH":
                            if line.count(",") != 1:
                                raise ValueError(self.error_text["pOH"])
                            x, c = (p.strip() for p in input.split(","))
                            if x == "" or c == "":
                                raise ValueError(self.error_text["pOH"])

                            result = chem.pOH(x, self.input_prep(c).value)
                            result = utils.round_pH(result, [self.prep_ev(c)])
                            output[pc] = result
                            pc += 1

                        case "EnhedKonvertering":
                            if line.count(",") != 1:
                                raise ValueError(self.error_text["EnhedKonvertering"])
                            start, unit = input.split(",")
                            if start == "" or unit == "":
                                raise ValueError(self.error_text["EnhedKonvertering"])
                            Qstart = self.input_prep(start)
                     
                  
                        

                            if unit.lower() == "si":
                                result = quantity.si_convert(Qstart)
                            else:
                                result = quantity.unit_convert(Qstart, unit)

                            output_unit = result.units
                            
                            output[pc] = round_quantity(result,[self.prep_ev(start)])
                            pc += 1

                        case "Analyse":
                            if line.count(",") != 0:
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


                            for part in input.split(","):
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
                            if line.count(",") != 1:
                                raise ValueError(self.error_text[procent_type])
                            top, bottom = input.split(",")
                            if top == "" or bottom == "":
                                raise ValueError(self.error_text[procent_type])


                            top_preped = self.input_prep(top)
                            bottom_preped = self.input_prep(bottom)

                            result = chem.procent(top_preped, bottom_preped)
                            
                          
                            output[pc] = f'{round_quantity(result,[self.prep_ev(top),self.prep_ev(bottom)])}%'
                            pc += 1

                        case 'DNATilPeptid':
                            if input.count(",") != 0:
                                raise ValueError(self.error_text["DNATilPeptid"])
                            if input == "":
                                raise ValueError(self.error_text["DNATilPeptid"])

                            output[pc] = biotek.DNA_to_peptide(input)
                            pc +=1
                                
                        case 'RNATilPeptid':
                            if input.count(",") != 0:
                                raise ValueError(self.error_text["RNATilPeptid"])
                            if input == "":
                                raise ValueError(self.error_text["RNATilPeptid"])

                            output[pc] = biotek.RNA_to_peptide(input)
                            pc +=1

                        case "MængdeBeregning":
                            if input.count(",") > 5:
                                raise ValueError(self.error_text["MængdeBeregning"])

                            if input == "":   
                                raise ValueError(self.error_text["MængdeBeregning"])
                           
                            tokens = input.split(",")


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

    def unit_bracket_strip(self, val):
        match = re.match(r"([^\[]+)\[([^\]]+)\]", val)
        if not match:
            raise ValueError(f"could not parse value/unit: {val!r}")

        num_str, unit = match.group(1), match.group(2)

        if "," in num_str:
            raise ValueError("Brug punktum som decimal tal ikke komma")

        value = float(num_str)

        return value, unit
