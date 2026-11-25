(async () => {
    const wait = ms => new Promise(r => setTimeout(r, ms));
    while (!spell.ready) await wait(50);
    let seed = 12345;
    const rand = n => { seed = (seed * 1103515245 + 12345) % 2147483648; return seed % n; };
    const morphemes = [...CHEM.keys()];

    const accepted = new Set();
    for (let t = 0; t < 60000 && accepted.size < 150; t++) {
        const parts = Array.from({ length: 2 + rand(3) }, () => morphemes[rand(morphemes.length)]);
        const w = parts.join("");
        if (w.length >= 6 && w.length <= 22 && spellChemical(w) && !spellInDict(w)) accepted.add(parts.join("|"));
    }
    console.log(`A) random combinations accepted (${accepted.size}):`);
    const list = [...accepted];
    for (let i = 0; i < list.length; i += 6) console.log("   " + list.slice(i, i + 6).join("   "));

    const real = "methan ethan propan butan hexan ethen propen ethyn methanol ethanol propanol propanon butanon ethanal methanal ethansyre methylamin diethylamin triethylamin dimethylpropan ethylendiamin cyclohexan cyclohexanol cyclohexen diethylether ethylacetat propandiol propantriol butadien dichlormethan tetrachlormethan methylbenzen dinitrogenpentaoxid carbondioxid hexaaquajern tetraamminkobber kaliumhexacyanoferrat natriumthiosulfat kaliumpermanganat natriumhydroxid natriumchlorid kaliumiodid calciumcarbonat natriumhydrogencarbonat ammoniumchlorid kobbersulfat sølvnitrat bariumsulfat magnesiumoxid hydrogenperoxid svovldioxid acetylsalicylsyre benzoesyre carboxylsyre ethylethanoat kaliumdichromat diethylamine propanone butanone dichloromethane methylbenzene cyclohexene ethanoate hexacyanoferrate thiosulfate potassium permanganate dimethylsulfoxid chlorbenzen nitrobenzen iodmethan methyliodid ethylbromid hydroxybenzen aminosyre ethanolamin glycerol benzoylchlorid tetrachloridocuprat dicyanidoargentat natriumcyanat kaliumthiocyanat hypochlorit".split(" ");
    const letters = "abcdefghijklmnopqrstuvwxyz";
    const mutate = w => {
        const i = rand(w.length), op = rand(4);
        if (op === 0) return w.slice(0, i) + w.slice(i + 1);
        if (op === 1) return w.slice(0, i) + letters[rand(26)] + w.slice(i);
        if (op === 2) return w.slice(0, i) + letters[rand(26)] + w.slice(i + 1);
        return i < w.length - 1 ? w.slice(0, i) + w[i + 1] + w[i] + w.slice(i + 2) : w;
    };
    const invented = new Map();
    let missed = 0, total = 0;
    for (const name of real) for (let k = 0; k < 4; k++) {
        let typo = mutate(name);
        if (k >= 2) typo = mutate(typo);
        if (typo === name || spellKnown(typo)) continue;
        total++;
        const s = spellSuggest(typo);
        if (!s.map(x => x.toLowerCase()).includes(name)) missed++;
        for (const c of s) if (!spellInDict(c) && !real.includes(c)) invented.set(c, `${typo}->${c}`);
    }
    console.log(`B) typos tested: ${total}, right name not among suggestions: ${missed}`);
    console.log(`   suggestions invented by the chemistry rules (${invented.size}):`);
    const inv = [...invented.values()];
    for (let i = 0; i < inv.length; i += 5) console.log("   " + inv.slice(i, i + 5).join("   "));
    console.log("DONE");
})();
