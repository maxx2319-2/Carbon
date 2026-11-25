(async () => {
    await window.spellReady;
    const da = "diethylamin triethylamin methylamin ethanol methanol propanol butanol propanon ethanal methanal ethansyre eddikesyre myresyre svovlsyre saltsyre salpetersyre phosphorsyre kulsyre natriumchlorid natriumhydroxid kaliumpermanganat kaliumiodid kaliumdichromat calciumcarbonat natriumhydrogencarbonat ammoniumchlorid kobbersulfat jernoxid sølvnitrat bariumsulfat magnesiumoxid cyclohexan cyclohexen benzen methylbenzen dichlormethan tetrachlormethan trichlormethan chloroform ammoniak ethylacetat ethylethanoat diethylether acetylsalicylsyre benzoesyre aminosyre carboxylsyre aldehyd keton alkohol alkan alken alkyn hexan pentan heptan octan ethen ethyn propen glucose saccharose fructose phenolphthalein bromthymolblåt methylorange hydrogenperoxid natriumthiosulfat kaliumhexacyanoferrat tetraamminkobber hexaaquajern carbondioxid carbonmonoxid dinitrogenpentaoxid svovldioxid natriumchloridopløsning kaliumpermanganatopløsning";
    const en = "diethylamine triethylamine methylamine ethanol methanol propanol butanol propanone ethanal methanal ethanoic acetic formic sulfuric sulphuric hydrochloric nitric phosphoric sodium chloride hydroxide potassium permanganate iodide dichromate calcium carbonate hydrogencarbonate bicarbonate ammonium sulfate sulphate oxide nitrate cyclohexane cyclohexene benzene methylbenzene toluene dichloromethane tetrachloromethane trichloromethane chloroform ammonia ethyl ethanoate diethyl ether acetylsalicylic benzoic amino carboxylic aldehyde ketone alcohol alkane alkene alkyne hexane pentane heptane octane ethene ethyne propene glucose sucrose fructose phenolphthalein bromothymol methyl orange peroxide thiosulfate hexacyanoferrate tetraamminecopper hexaaquairon dioxide monoxide dinitrogen pentoxide";
    const typos = "beregnign koncentartion equilbrium molkeyle konstnaten hjemmeopgvae opløsnign temperatru reaktoin recieve seperate definately occured untill wierd begyndte_ bestemmmelse ligevægtskonstnat hastighde forsøgt_ diethylamien cyclohexna hexnae methnol permanganta kaliumpermangant sulfrat ethanoik dichlormetahn natriumklorid bromthymolbalt".split(" ").filter(w => !w.endsWith("_"));

    for (const [name, list] of [["DA names", da], ["EN names", en]]) {
        const words = list.split(" ");
        const bad = words.filter(w => !isKnown(w));
        console.log(`${name}: ${words.length - bad.length}/${words.length} accepted`);
        for (const w of bad) console.log(`  still flagged: ${w}`);
    }

    const missed = typos.filter(w => isKnown(w));
    console.log(`typos: ${typos.length - missed.length}/${typos.length} still caught`);
    for (const w of missed) console.log(`  NOT caught: ${w}`);
    for (const w of typos.filter(w => !isKnown(w))) {
        const t = performance.now();
        console.log(`  ${w} -> ${suggest(w, 3).join(", ") || "(ingen forslag)"} | autocorrect: ${fixFor(w) ?? "-"} (${Math.round(performance.now() - t)} ms)`);
    }

    const all = [...da.split(" "), ...en.split(" ")];
    const broken = all.map(w => [w, fixFor(w)]).filter(([w, f]) => f && !isKnown(w));
    console.log(`autocorrect would change a correct name: ${broken.length ? broken.map(([w, f]) => `${w}->${f}`).join(", ") : "never"}`);

    const line = lines()[5];
    line.value = "\\text{Vi blander propan-2-ol, 2-methylpropan-1-ol og but-2-en med kobber(II)sulfat og N,N-diethylamin}";
    console.log(`hyphen line flagged: ${misspelled(line, true).map(w => w.text).join(", ") || "-"}`);
    line.value = "\\text{Vi blander propan-2-ol med 2-methylpropan-1-ol og kobbber}";
    console.log(`hyphen line with typo flagged: ${misspelled(line, true).map(w => w.text).join(", ") || "-"}`);
    console.log("DONE");
})();
