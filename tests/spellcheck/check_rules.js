(async () => {
    const wait = ms => new Promise(r => setTimeout(r, ms));
    while (!spell.ready) await wait(50);
    const real = "methan ethan propan butan pentan hexan heptan octan ethen propen ethyn propyn methanol ethanol propanol propanon butanon ethanal methanal ethansyre methylamin diethylamin triethylamin trimethylamin dimethylpropan methylethylketon ethylendiamin ethandiamin cyclohexan cyclohexanol cyclohexen methylcyclohexan diethylether dipropylether ethylacetat ethylethanoat propandiol propantriol hexandion butadien hexadien dichlormethan tetrachlormethan trichlormethan methylbenzen pentoxide dinitrogenpentaoxid carbondioxid hexaaquajern tetraamminkobber kaliumhexacyanoferrat natriumthiosulfat alkan alken alkyn alkyl alkane alkene alkyne methyl ethyl propyl butyl diethyl ethanoic methanoic propanoic butanoic ethanoate propanone butanone hexane cyclohexane cyclohexene dichloromethane tetrachloromethane methylbenzene acetylsalicylic hydrochloric sulfuric nitric phosphoric carboxylic benzoic acetic formic bromothymol thiosulfate hexacyanoferrate tetraamminecopper hexaaquairon dioxide peroxide ethoxyethan methoxybenzen dimethoxymethan glycerol benzoyl benzoylchlorid acetylchlorid cupric auric ferricyanid ferrocyanid ethanolamin propenol ethenyl disulfid phosphide glycol ethylenglycol propanal butanal ethanoyl".split(" ");
    const fake = "diethamin diethynamin dihexamin diblyamin dibutan diethan dimethan ethamin methamin propamin butamin hexacyanotert dichlorometa dienylamin diatylamin ethylan diethylan methan_ ethpropan methethan dihexan tripentan butprop hexacyanoferr propanonane propanonene propanonone methol ethol ethanen propanenol hexacyanocupr dinitr hexacyanoferro kaliumpermangan permanganit kaliumpermanganit permangan".split(" ").filter(w => !w.endsWith("_"));
    const badReal = real.filter(w => !spellChemical(w) && !spellKnown(w));
    const badFake = fake.filter(w => spellChemical(w));
    console.log(`real names accepted: ${real.length - badReal.length}/${real.length} ${badReal.length ? "| REJECTED: " + badReal.join(", ") : ""}`);
    console.log(`fake names rejected by chemistry rule: ${fake.length - badFake.length}/${fake.length} ${badFake.length ? "| ACCEPTED: " + badFake.join(", ") : ""}`);
    console.log(`fake names still accepted somewhere (dictionary/compound): ${fake.filter(w => spellKnown(w)).join(", ") || "-"}`);

    console.log("--- suggestions ---");
    for (const w of ["diehyamin", "dietylamn", "metylbensen", "etylacetta", "dietyleter", "cyklohexne", "dichlormetan", "etan", "eten", "etanol", "bensen", "hexacyanofert", "acetylsalicylsyr", "kaliumpermangant", "propanonne", "Diehyamin"]) {
        const t = performance.now();
        const s = spellSuggest(w);
        const fakes = s.filter(c => fake.includes(c.toLowerCase()) || (!spellInDict(c) && !spellChemical(c.toLowerCase()) && !spellCompound(c.toLowerCase())));
        console.log(`${w}: ${s.join(", ") || "(ingen forslag)"} (${Math.round(performance.now() - t)} ms)${fakes.length ? "  <-- INVALID: " + fakes.join(", ") : ""}`);
    }
    console.log("DONE");
})();
