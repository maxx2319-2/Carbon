import re

# nedavnings mønstre


class node:
    def __init__(self, name, type, carrier, gen, x, y):
        self.name = name
        self.type = type
        self.carrier = carrier
        self.x = x
        self.y = y
        self.gen = gen


class graph:
    def __init__(self):
        self.nodes = {}
        self.M_amount = 0
        self.F_amount = 0

    def add_node(self, name, x, y, gen, type):
        self.nodes[name] = node(name, type, x=x, y=y, carrier=False, gen=gen)


# DNA til peptid

DNA_CODON_TABLE = {
    "TTT": "Phe",
    "TTC": "Phe",
    "TTA": "Leu",
    "TTG": "Leu",
    "CTT": "Leu",
    "CTC": "Leu",
    "CTA": "Leu",
    "CTG": "Leu",
    "ATT": "Ile",
    "ATC": "Ile",
    "ATA": "Ile",
    "ATG": "Met",
    "GTT": "Val",
    "GTC": "Val",
    "GTA": "Val",
    "GTG": "Val",
    "TCT": "Ser",
    "TCC": "Ser",
    "TCA": "Ser",
    "TCG": "Ser",
    "CCT": "Pro",
    "CCC": "Pro",
    "CCA": "Pro",
    "CCG": "Pro",
    "ACT": "Thr",
    "ACC": "Thr",
    "ACA": "Thr",
    "ACG": "Thr",
    "GCT": "Ala",
    "GCC": "Ala",
    "GCA": "Ala",
    "GCG": "Ala",
    "TAT": "Tyr",
    "TAC": "Tyr",
    "TAA": "Stop",
    "TAG": "Stop",
    "CAT": "His",
    "CAC": "His",
    "CAA": "Gln",
    "CAG": "Gln",
    "AAT": "Asn",
    "AAC": "Asn",
    "AAA": "Lys",
    "AAG": "Lys",
    "GAT": "Asp",
    "GAC": "Asp",
    "GAA": "Glu",
    "GAG": "Glu",
    "TGT": "Cys",
    "TGC": "Cys",
    "TGA": "Stop",
    "TGG": "Trp",
    "CGT": "Arg",
    "CGC": "Arg",
    "CGA": "Arg",
    "CGG": "Arg",
    "AGT": "Ser",
    "AGC": "Ser",
    "AGA": "Arg",
    "AGG": "Arg",
    "GGT": "Gly",
    "GGC": "Gly",
    "GGA": "Gly",
    "GGG": "Gly",
}

RNA_CODON_TABLE = {
    "UUU": "Phe",
    "UUC": "Phe",
    "UUA": "Leu",
    "UUG": "Leu",
    "CUU": "Leu",
    "CUC": "Leu",
    "CUA": "Leu",
    "CUG": "Leu",
    "AUU": "Ile",
    "AUC": "Ile",
    "AUA": "Ile",
    "AUG": "Met",
    "GUU": "Val",
    "GUC": "Val",
    "GUA": "Val",
    "GUG": "Val",
    "UCU": "Ser",
    "UCC": "Ser",
    "UCA": "Ser",
    "UCG": "Ser",
    "CCU": "Pro",
    "CCC": "Pro",
    "CCA": "Pro",
    "CCG": "Pro",
    "ACU": "Thr",
    "ACC": "Thr",
    "ACA": "Thr",
    "ACG": "Thr",
    "GCU": "Ala",
    "GCC": "Ala",
    "GCA": "Ala",
    "GCG": "Ala",
    "UAU": "Tyr",
    "UAC": "Tyr",
    "UAA": "Stop",
    "UAG": "Stop",
    "CAU": "His",
    "CAC": "His",
    "CAA": "Gln",
    "CAG": "Gln",
    "AAU": "Asn",
    "AAC": "Asn",
    "AAA": "Lys",
    "AAG": "Lys",
    "GAU": "Asp",
    "GAC": "Asp",
    "GAA": "Glu",
    "GAG": "Glu",
    "UGU": "Cys",
    "UGC": "Cys",
    "UGA": "Stop",
    "UGG": "Trp",
    "CGU": "Arg",
    "CGC": "Arg",
    "CGA": "Arg",
    "CGG": "Arg",
    "AGU": "Ser",
    "AGC": "Ser",
    "AGA": "Arg",
    "AGG": "Arg",
    "GGU": "Gly",
    "GGC": "Gly",
    "GGA": "Gly",
    "GGG": "Gly",
}


def DNA_to_peptide(dna_seq):
    split = dna_seq.split()
    for part in split:
        if len(part) % 3 == 0:
            continue
        else:
            return "Error kodon længder er ikke rigtige"

    if len(dna_seq.replace(" ", "")) % 3 == 0:
        codons = re.findall("...", (dna_seq.upper()).replace(" ", ""))

        invalid = [c for c in codons if c not in DNA_CODON_TABLE]
        if invalid:
            return f"Error ukendt kodon {invalid}"

        return ", ".join(DNA_CODON_TABLE[codon] for codon in codons)
    else:
        return "Error Antal baser skal gå op i 3"


def RNA_to_peptide(rna_seq):
    split = rna_seq.split()
    for part in split:
        if len(part) % 3 == 0:
            continue
        else:
            return "Error kodon længder er ikke rigtige"

    if len(rna_seq.replace(" ", "")) % 3 == 0:
        codons = re.findall("...", (rna_seq.upper()).replace(" ", ""))

        invalid = [c for c in codons if c not in RNA_CODON_TABLE]
        if invalid:
            return f"Error ukendt kodon {invalid}"

        return ", ".join(RNA_CODON_TABLE[codon] for codon in codons)

    else:
        return "Error Antal baser skal gå op i 3"


def mutation_analyse(rask, muteret):
    if rask == muteret:
        return ["Ingen mutation, begge strenge er det samme"]

    start = 0
    while start < min(len(rask), len(muteret)) and rask[start] == muteret[start]:
        start += 1
    end = len(rask)
    end_mut = len(muteret)
    while end > start and end_mut > start and rask[end - 1] == muteret[end_mut -1]:
        end -= 1
        end_mut -= 1

    diff = len(muteret) - len(rask)
    if diff != 0:
        n = abs(diff)
        kind = "Insertion" if diff > 0 else "Deletion"
        bases = "base" if n == 1 else "baser"
        shift = "In frame mutation" if n % 3 == 0 else "Frameshift mutation"
        return [f"{kind} af {n} {bases} ved base nr {start + 1}. {shift}"]

    if len(rask) % 3 != 0:
        raise ValueError("Kodon længderne går ikke op i 3")

    to_peptide = RNA_to_peptide if "U" in rask + muteret else DNA_to_peptide
    peptide_sick = [p.strip() for p in to_peptide(muteret).split(",")]
    peptide_healthy = [p.strip() for p in to_peptide(rask).split(",")]

    output = []
    for i in range(start, end):
        if rask[i] == muteret[i]:
            continue
        amino_sick = peptide_sick[i // 3]
        amino_healthy = peptide_healthy[i // 3]
        if amino_healthy == amino_sick:
            output.append(f"Tavs mutation ved base nr {i + 1}")
        elif amino_sick == "Stop":
            output.append(f"Nonsensmutation ved base nr {i + 1}")
        else:
            output.append(f"Missensmutation ved base nr {i + 1}")

    return output