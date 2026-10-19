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
            return "Error codon længder er ikke rigtige"

    if len(dna_seq.replace(" ", "")) % 3 == 0:
        codons = re.findall("...", (dna_seq.upper()).replace(" ", ""))

        invalid = [c for c in codons if c not in DNA_CODON_TABLE]
        if invalid:
            return f"Error ukendt codon {invalid}"

        result = ""
        for codon in codons:
            x = DNA_CODON_TABLE[codon]
            result += f"{x}, "

        return result
    else:
        return "Error Antal baser skal gå op i 3"


def RNA_to_peptide(rna_seq):
    split = rna_seq.split()
    for part in split:
        if len(part) % 3 == 0:
            continue
        else:
            return "Error codon længder er ikke rigtige"

    if len(rna_seq.replace(" ", "")) % 3 == 0:
        codons = re.findall("...", (rna_seq.upper()).replace(" ", ""))

        invalid = [c for c in codons if c not in RNA_CODON_TABLE]
        if invalid:
            return f"Error ukendt codon {invalid}"

        result = ""
        for codon in codons:
            x = RNA_CODON_TABLE[codon]
            result += f"{x}, "

        return result
    else:
        return "Error Antal baser skal gå op i 3"


def mutation_analyse(rask, muteret, dr):
    compared = []
    divergence = None
    mutations = {}
    if len(rask) != len(muteret):
        raise ValueError("Sequences must be the same length")

    output = []

    for i, (a, b) in enumerate(zip(rask, muteret)):
        if a == b:
            compared.append("I")
        else:
            compared.append("M")
            mutations[i] = [a, b]
            if divergence is None:
                divergence = i

    if divergence is None:
        return ["Ingen mutation begge strenge er det samme"]

    max_shift = 12
    best_shift = None
    for shift in list(range(1, max_shift + 1)) + list(range(-1, -max_shift - 1, -1)):
        a_tail = rask[divergence:]
        b_tail = muteret[divergence + shift :] if shift > 0 else muteret[divergence:]
        a_cmp = rask[divergence - shift :] if shift < 0 else a_tail
        b_cmp = b_tail if shift > 0 else muteret[divergence:]

        n = min(len(a_cmp), len(b_cmp))
        if n < 4:
            continue
        matches = sum(1 for x, y in zip(a_cmp[:n], b_cmp[:n]) if x == y)
        if matches / n > 0.8:
            best_shift = shift
            break

    if best_shift is not None and best_shift % 3 != 0:
        total_gramatik_død = ""
        if best_shift == 1:
            total_gramatik_død = "base"
        else:
            total_gramatik_død = "baser"
        return [
            f"Frameshift mutation. Forskydning på {best_shift} {total_gramatik_død} ved base nr {divergence + 1}"
        ]
    elif best_shift is not None:
        return [
            f"In frame mutation. Forskydning på {best_shift} baser ved base nr {divergence + 1}"
        ]

    if dr == "DNA":
        peptide_sick = [
            p.strip() for p in DNA_to_peptide(muteret).split(",") if p.strip()
        ]
        peptide_healthy = [
            p.strip() for p in DNA_to_peptide(rask).split(",") if p.strip()
        ]
    elif dr == "RNA":
        peptide_sick = [
            p.strip() for p in RNA_to_peptide(muteret).split(",") if p.strip()
        ]
        peptide_healthy = [
            p.strip() for p in RNA_to_peptide(rask).split(",") if p.strip()
        ]

    for i, part in enumerate(compared):
        if part == "M":
            amino_sick = peptide_sick[i // 3]
            amino_healthy = peptide_healthy[i // 3]

            if amino_healthy == amino_sick:
                output.append(f"Tavs mutation ved base nr {i + 1}")
            elif amino_sick == "Stop":
                output.append(f"Nonsense mutation ved base nr {i + 1}")
            else:
                output.append(f"Missense mutation ved base nr {i + 1}")

    return output
