import parser
import utils
import chem
from quantity import quantity
import re
import biotek
import json
from types import SimpleNamespace

from path import resource_path

with open(resource_path("config.json")) as f:
    config = json.load(f, object_hook=lambda d: SimpleNamespace(**d))


def as_expr(q):
    parts = [repr(q.value)] + [f"{u}^({p})" for u, p in q.units.items()]
    return "(" + "*".join(parts) + ")"


class Variables:
    def __init__(self, value, var_type):
        self.value = str(value)
        self.var_type = str(var_type)


class EV:
    def __init__(self):
        self.variables = {}
        self._pattern = None
        self._pattern_dirty = True
        self.functions = [
            "help",
            "balance_reaction",
            "pH",
            "SI",
            "analysis",
            "bjerrumdiagram",
            "udbytteprocent",
            "volumenprocent",
            "masseprocent",
            "DNA_til_peptid",
            "RNA_til_peptid",
            "mængdeberegning",
            "puffer",
            "mutations_analyse_DNA",
            "mutations_analyse_RNA",
            "unit_convert",
            "pH_to_concentration",
            "pOH_to_concentration",
            "pOH",
            "empirisk_analyse",
        ]

    def ev(self, s):
        output = {}

        lines = s.splitlines()

        pc = 0
        while pc < len(lines):
            line = lines[pc]

            if line.strip() == "":
                pc += 1
                continue

            line = re.sub(r"(\d)\s+\[", r"\1[", line)
            
            try:
                match line.split(maxsplit=1)[0]:

                    
                    case "balance_reaction":
                        _,medium,expr = line.split(maxsplit=2)
                        if medium == "None":
                            medium = None

                        result = chem.balance_reaction(expr,medium)
                        output[pc] = result
                        pc += 1

                    case "pH":
                        expr = line.split(maxsplit=1)[1]
                        x, c = expr.split(maxsplit=1)
                        c_count = re.findall(r"\d+\.?\d*|[^\d]+", c)[0]
                   
                        c = str(quantity.si_convert(parser.evaluate(self.prep_ev(c))))
                        c = c.split(maxsplit=1)[0]
                        result = chem.pH(x, c)
                        result = utils.round_pH(result,[c_count])
                        output[pc] = result
                        pc += 1



                    case "pOH":
                        expr = line.split(maxsplit=1)[1]
                        x, c = expr.split(maxsplit=1)
                        c_count = re.findall(r"\d+\.?\d*|[^\d]+", c)[0]
                    
                        c = str(quantity.si_convert(parser.evaluate(self.prep_ev(c))))
                        c = c.split(maxsplit=1)[0]
                        result = chem.pOH(x, c)
                        result = utils.round_pH(result,[c_count])
                        output[pc] = result
                        pc += 1
                    

                    case "SI":
                        expr = line.split(maxsplit=1)[1]
                        result = quantity.si_convert(
                            parser.evaluate(self.prep_ev(expr))
                        )

                        output[pc] = result
                        pc += 1

                    case "unit_convert":
                        expr = line.split(maxsplit=1)[1]
                        q,unit = expr.split(maxsplit = 1)

                        qv,qu = self.unit_bracket_strip(q)
                        
                        

                        Q = quantity.quantity_convert(qv,qu)
                        result = quantity.unit_convert(Q,unit)
                        output[pc] = result
                        pc += 1


                    case "analysis":
                        expr = line.split(maxsplit=1)[1]
                        molecule, emp, mol, count, procent, dbe = (
                            chem.elemental_analasis(expr)
                        )
                        indhold = f"Masse procent:\n{'\n'.join(procent)}"
                        output[pc] = (
                            f"Molekyle: {molecule}\n Empirisk formel: {emp}\n Molar masse: {round(mol,config.rounding_decimals)}\n DBE: {dbe} \n Antal atomer: {count} \n {indhold}"
                        )
                        pc += 1

                    case "bjerrumdiagram":
                        expr = line.split(maxsplit=1)[1]
                        acids = expr.split(",")
                        acids = [float(a) for a in acids]
                        chem.bjerrum(acids)
                        pc += 1

                    

                    case "udbytteprocent" | "volumenprocent" | "masseprocent":
                        expr = line.split(maxsplit=1)[1]
                        top, bottom = expr.split()
                        top_count = re.findall(r"\d+\.?\d*|[^\d]+", top)[0]
                        bottom_count = re.findall(r"\d+\.?\d*|[^\d]+", bottom)[0]

                        top = str(
                            quantity.si_convert(parser.evaluate(self.prep_ev(top)))
                        )
                        top = top.split(maxsplit=1)[0]
                        bottom = str(
                            quantity.si_convert(parser.evaluate(self.prep_ev(bottom)))
                        )
                        bottom = bottom.split(maxsplit=1)[0]
                        result = chem.procent(float(bottom),float(top))

                        output[pc] = f"{utils.significant_figures(result,[top_count,bottom_count])}%"
                        pc += 1

                    case "RNA_til_peptid":
                        expr = line.split(maxsplit=1)[1]
                        result = biotek.RNA_to_peptide(expr)
                        output[pc] = result
                        pc += 1

                    case "DNA_til_peptid":
                        expr = line.split(maxsplit=1)[1]
                        result = biotek.DNA_to_peptide(expr)
                        output[pc] = result
                        pc += 1

                    case "mængdeberegning":
                        expr = line.split(maxsplit=1)[1]
                        tokens = expr.split()

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
                    

                    case "puffer":
                        expr = line.split(maxsplit=1)[1]
                        syre_raw, base_raw, pKs = expr.split()

                        syre_val = str(
                            quantity.si_convert(parser.evaluate(self.prep_ev(syre_raw)))
                        )
                        syre_val = syre_val.split(maxsplit=1)[0]

                        base_val = str(
                            quantity.si_convert(parser.evaluate(self.prep_ev(base_raw)))
                        )
                        base_val = base_val.split(maxsplit=1)[0]

                        result = chem.puffer(
                            float(syre_val), float(base_val), float(pKs)
                        )
                        output[pc] = utils.round_pH(result,[syre_raw,base_raw])
                        pc += 1

                    case "mutations_analyse_DNA":
                        expr = line.split(maxsplit=1)[1]

                        rask, muteret = expr.split(",")
                        rask = rask.replace(" ", "")
                        muteret = muteret.replace(" ", "")

                        result = biotek.mutation_analyse(rask, muteret, "DNA")
                        result = f"mutationer:\n{'\n'.join(result)}"
                        output[pc] = result
                        pc += 1

                    case "mutations_analyse_RNA":
                        expr = line.split(maxsplit=1)[1]

                        rask, muteret = expr.split(",")
                        rask = rask.replace(" ", "")
                        muteret = muteret.replace(" ", "")

                        result = biotek.mutation_analyse(rask, muteret, "RNA")
                        result = f"mutationer:\n{'\n'.join(result)}"
                        output[pc] = result
                        pc += 1


                    case "pH_to_concentration":
                        expr = line.split(maxsplit=1)[1]
                        r1,r2 = chem.pH_to_concentration(float(expr))
                        output[pc] = f'[H3O+]: {r1:e} mol/l \n [OH-]: {r2:e} mol/l'
                        pc +=1

                    case "pOH_to_concentration":
                        expr = line.split(maxsplit=1)[1]
                        r1,r2 = chem.pH_to_concentration(float(expr))
                        output[pc] = f'[OH-]: {r1:e} mol/l \n [H3O+]: {r2:e} mol/l'
                        pc +=1


                    case "empirisk_analyse":
                        expr = line.split(maxsplit=1)[1]
                        output[pc] = chem.emperical_analysis(expr)
                        pc +=1

                    case "help":
                        indhold = f'{'\n'.join(self.functions)}'
                        output[pc] = indhold
                        pc += 1

                    case "#":
                        pc += 1

                    case _:
                        raise ValueError("Error ukendt function")

                      

                    

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
            parts = re.split(r"(\[[^\]]*\])", expr)   # bracket parts land on odd indexes
            for i in range(0, len(parts), 2):
                parts[i] = pattern.sub(lambda m: self.variables[m.group(0)].value, parts[i])
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