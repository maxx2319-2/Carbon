(async () => {
    const wait = ms => new Promise(r => setTimeout(r, ms));
    while (!spell.ready) await wait(50);
    const must = "hexacyanoferrat kaliumhexacyanoferrat hexacyanoferrate tetrachloridocuprat tetrachlorocuprate dicyanidoargentat dicyanoargentate tetrachloridoaurat hexahydroxostannat natriumstannit natriumplumbit plumbat stannat ferrat cuprat argentat aurat cupric cuprous ferric ferrous auric ferricyanid ferrocyanid acetylen phenylen sulfan phosphan".split(" ");
    const mustNot = "hexacyanoferrit hexacyanoferrite tetrachloridocuprit dicyanidoargentit aurit hexacyanoferrito hexacyanoferrid ferrid cuprol hexacyanoenit cyanoen chloren carbonan ammonan".split(" ");
    console.log(`complexes and salts accepted: ${must.filter(w => spellKnown(w)).length}/${must.length} ${must.filter(w => !spellKnown(w)).map(w => "| FLAGGED " + w).join(" ")}`);
    console.log(`-it after ferr/cupr/argent/aur rejected by chemistry rule: ${mustNot.filter(w => !spellChemical(w)).length}/${mustNot.length} ${mustNot.filter(w => spellChemical(w)).map(w => "| ACCEPTED " + w).join(" ")}`);
    for (const w of ["hexacyanofert", "hexacyanoferit", "tetrachloridocuprt", "kaliumhexacyanoferat"]) console.log(`${w} -> ${spellSuggest(w).join(", ") || "(ingen forslag)"}`);
    console.log("DONE");
})();
