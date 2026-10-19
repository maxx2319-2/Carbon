import pytest
import biotek

# Met Ala Ile Val Met Gly Arg Stop Lys Gly Ala Arg
HEALTHY = "ATGGCCATTGTAATGGGCCGCTGAAAGGGTGCCCGA"


def point_mutation(seq, base_nr, new):
    i = base_nr - 1
    return seq[:i] + new + seq[i + 1:]


def insertion(seq, base_nr, bases):
    # cut to the same length, since mutation_analyse needs two equally long strands
    i = base_nr - 1
    return (seq[:i] + bases + seq[i:])[:len(seq)]


# --- codon tables ---

def test_codon_tables_have_all_64_codons():
    assert len(biotek.DNA_CODON_TABLE) == 64
    assert len(biotek.RNA_CODON_TABLE) == 64


def test_rna_table_matches_dna_table():
    for codon, amino in biotek.DNA_CODON_TABLE.items():
        assert biotek.RNA_CODON_TABLE[codon.replace("T", "U")] == amino


def test_stop_codons():
    assert sorted(c for c, a in biotek.DNA_CODON_TABLE.items() if a == "Stop") == ["TAA", "TAG", "TGA"]


def test_twenty_amino_acids():
    assert len(set(biotek.DNA_CODON_TABLE.values()) - {"Stop"}) == 20


def test_only_one_codon_for_met_and_trp():
    assert [c for c, a in biotek.DNA_CODON_TABLE.items() if a == "Met"] == ["ATG"]
    assert [c for c, a in biotek.DNA_CODON_TABLE.items() if a == "Trp"] == ["TGG"]


# --- translation ---

@pytest.mark.parametrize("seq, expected", [
    ("ATGAAA", "Met, Lys, "),
    ("atgaaa", "Met, Lys, "),
    ("ATG AAA", "Met, Lys, "),
    ("ATGTAAAAA", "Met, Stop, Lys, "),      # carries on after a stop codon
    ("", ""),
])
def test_DNA_to_peptide(seq, expected):
    assert biotek.DNA_to_peptide(seq) == expected


@pytest.mark.parametrize("seq", ["ATGA", "ATG AA A", "ATGAAAT"])
def test_DNA_wrong_length(seq):
    assert biotek.DNA_to_peptide(seq) == "Error codon længder er ikke rigtige"


@pytest.mark.parametrize("seq, bad", [
    ("XYZ", "['XYZ']"),
    ("ATGXXX", "['XXX']"),
    ("AUG", "['AUG']"),     # RNA given to the DNA function
])
def test_DNA_unknown_codon(seq, bad):
    assert biotek.DNA_to_peptide(seq) == f"Error ukendt codon {bad}"


@pytest.mark.parametrize("seq, expected", [
    ("AUGUUU", "Met, Phe, "),
    ("augguu", "Met, Val, "),
    ("AUG UUU", "Met, Phe, "),
    ("", ""),
])
def test_RNA_to_peptide(seq, expected):
    assert biotek.RNA_to_peptide(seq) == expected


def test_RNA_wrong_length():
    assert biotek.RNA_to_peptide("AUGA") == "Error codon længder er ikke rigtige"


def test_RNA_unknown_codon():
    assert biotek.RNA_to_peptide("ATG") == "Error ukendt codon ['ATG']"


def test_DNA_and_RNA_give_same_peptide():
    assert biotek.DNA_to_peptide(HEALTHY) == biotek.RNA_to_peptide(HEALTHY.replace("T", "U"))


# --- mutation analysis ---

def test_no_mutation():
    assert biotek.mutation_analyse(HEALTHY, HEALTHY, "DNA") == ["Ingen mutation begge strenge er det samme"]


@pytest.mark.parametrize("base_nr, new, expected", [
    (6, "T", "Tavs mutation ved base nr 6"),            # GCC -> GCT, still Ala
    (7, "C", "Missense mutation ved base nr 7"),        # ATT -> CTT, Ile -> Leu
    (25, "T", "Nonsense mutation ved base nr 25"),      # AAG -> TAG, Lys -> Stop
    (36, "T", "Tavs mutation ved base nr 36"),          # CGA -> CGT, last base
])
def test_point_mutation(base_nr, new, expected):
    assert biotek.mutation_analyse(HEALTHY, point_mutation(HEALTHY, base_nr, new), "DNA") == [expected]


def test_two_point_mutations():
    mutated = point_mutation(point_mutation(HEALTHY, 6, "T"), 7, "C")
    assert biotek.mutation_analyse(HEALTHY, mutated, "DNA") == [
        "Tavs mutation ved base nr 6",
        "Missense mutation ved base nr 7",
    ]


def test_point_mutation_in_RNA():
    rna = HEALTHY.replace("T", "U")
    assert biotek.mutation_analyse(rna, point_mutation(rna, 7, "C"), "RNA") == ["Missense mutation ved base nr 7"]


@pytest.mark.parametrize("bases, expected", [
    ("T", "Frameshift mutation. Forskydning på 1 base ved base nr 10"),
    ("TT", "Frameshift mutation. Forskydning på 2 baser ved base nr 10"),
    ("TTT", "In frame mutation. Forskydning på 3 baser ved base nr 10"),
])
def test_insertion(bases, expected):
    assert biotek.mutation_analyse(HEALTHY, insertion(HEALTHY, 10, bases), "DNA") == [expected]


def test_deletion_is_frameshift():
    deleted = HEALTHY[:9] + HEALTHY[10:] + "A"
    [result] = biotek.mutation_analyse(HEALTHY, deleted, "DNA")
    assert result.startswith("Frameshift mutation.")
    assert result.endswith("ved base nr 10")


def test_mutation_analyse_needs_same_length():
    with pytest.raises(ValueError, match="same length"):
        biotek.mutation_analyse("ATG", "ATGA", "DNA")


# --- pedigree ---

def test_graph_add_node():
    g = biotek.graph()
    g.add_node("Ole", x=1, y=2, gen="Aa", type="M")
    node = g.nodes["Ole"]
    assert (node.name, node.x, node.y, node.gen, node.type, node.carrier) == ("Ole", 1, 2, "Aa", "M", False)
