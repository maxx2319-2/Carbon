(async () => {
    const wait = ms => new Promise(r => setTimeout(r, ms));
    while (!spell.ready) await wait(50);
    const heldOut = "diethylamin triethylamin methylamin ethanol methanol propanol butanol propanon ethanal methanal ethansyre natriumchlorid natriumhydroxid kaliumpermanganat kaliumiodid kaliumdichromat calciumcarbonat natriumhydrogencarbonat ammoniumchlorid kobbersulfat jernoxid sølvnitrat bariumsulfat magnesiumoxid cyclohexan cyclohexen benzen methylbenzen dichlormethan tetrachlormethan trichlormethan ethylacetat ethylethanoat diethylether acetylsalicylsyre carboxylsyre hexan pentan heptan octan ethen ethyn propen hydrogenperoxid natriumthiosulfat kaliumhexacyanoferrat tetraamminkobber hexaaquajern carbondioxid dinitrogenpentaoxid svovldioxid diethylamine triethylamine methylamine propanone ethanoic acetic formic sulfuric hydrochloric nitric phosphoric cyclohexane cyclohexene methylbenzene dichloromethane tetrachloromethane trichloromethane ethanoate hexane pentane heptane octane ethene ethyne propene thiosulfate hexacyanoferrate tetraamminecopper hexaaquairon dinitrogen pentoxide butadien hexadien propandiol hexandion ethoxyethan methoxybenzen glycerol benzoylchlorid acetylchlorid ethanolamin propenol ethenyl disulfid ethylenglycol propanal butanal tetrachloridocuprat dicyanidoargentat tetrachloridoaurat hexahydroxostannat natriumstannit natriumplumbit diethyliodid iodmethan chlormethan brommethan methyliodid ethylbromid iodsyre aminosyre nitrobenzen hydroxybenzen chlorbenzen fluorbenzen dimethylsulfoxid kaliumcyanat isocyanat butylamin dibutylamin methylpropylamin ethylpentan dimethylhexan chlorbutan dibromethan tetrabrommethan trichlorbenzen kaliumbromat natriumiodat lithiumhydroxid strontiumnitrat zinknitrat kobberhydroxid aluminiumsulfat bromethan iodethan propylbenzen butanon hexanol pentanol heptanol cyclopentanol methylcyclopentan".split(" ");
    let seed = 999;
    const rand = n => { seed = (seed * 1103515245 + 12345) % 2147483648; return seed % n; };
    const letters = "abcdefghijklmnopqrstuvwxyz";
    const mutate = w => {
        const i = rand(w.length), op = rand(4);
        if (op === 0) return w.slice(0, i) + w.slice(i + 1);
        if (op === 1) return w.slice(0, i) + letters[rand(26)] + w.slice(i);
        if (op === 2) return w.slice(0, i) + letters[rand(26)] + w.slice(i + 1);
        return i < w.length - 1 ? w.slice(0, i) + w[i + 1] + w[i] + w.slice(i + 2) : w;
    };
    let total = 0, accepted = 0, found = 0;
    const invented = new Map();
    const t0 = performance.now();
    for (const name of heldOut) for (let k = 0; k < 4; k++) {
        let typo = mutate(name);
        if (k >= 2) typo = mutate(typo);
        if (typo === name) continue;
        if (spellKnown(typo)) { accepted++; continue; }
        total++;
        const s = spellSuggest(typo).map(x => x.toLowerCase());
        if (s.includes(name)) found++;
        for (const c of s) if (!spellInDict(c) && !heldOut.includes(c) && !PLAUS_TRAIN.includes(c)) invented.set(c, typo + "->" + c);
    }
    console.log(`typos: ${total} flagged, ${accepted} wrongly accepted | right name suggested ${found}/${total} | ${Math.round((performance.now() - t0) / (total + accepted))} ms per typo`);
    console.log(`invented suggestions: ${invented.size}`);
    const list = [...invented.keys()].sort();
    for (let i = 0; i < list.length; i += 10) console.log("   " + list.slice(i, i + 10).join("  "));
    console.log("DONE");
})();
