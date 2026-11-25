(async () => {
    const wait = ms => new Promise(r => setTimeout(r, ms));
    while (!spell.ready) await wait(50);
    const words = "cyanat kaliumcyanat thiocyanat kaliumthiocyanat isocyanat ammoniumthiocyanat natriumcyanat cyanate thiocyanate bromit hypobromit iodit hypoiodit chloral hydroxyl hydroxylamin chlorid bromid iodid fluorid cyanid chlorat bromat iodat chlorit hypochlorit hydrochloric hydrobromic hydrocyanic chlorous sulfonat sulfonsyre dimethylsulfoid sulfoid".split(" ");
    const before = new Map(words.map(w => [w, spellKnown(w)]));
    const step = spellChemStep;
    spellChemStep = (state, m, kind) => kind === 0 && state >> 4 === 9 && !["ic", "ous"].includes(m) ? -1 : step(state, m, kind);
    spell.known.clear();
    spell.parts.clear();
    const changed = words.filter(w => before.get(w) !== spellKnown(w));
    console.log("words whose result changes: " + (changed.map(w => `${w} (${before.get(w) ? "ok" : "flag"} -> ${spellKnown(w) ? "ok" : "flag"})`).join(", ") || "none"));
    console.log("unchanged: " + words.filter(w => !changed.includes(w)).map(w => `${w}=${spellKnown(w) ? "ok" : "flag"}`).join(" "));
    console.log("dimethylsulfxid -> " + spellSuggest("dimethylsulfxid").join(", "));
    console.log("DONE");
})();
