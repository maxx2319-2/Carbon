(async () => {
    const wait = ms => new Promise(r => setTimeout(r, ms));
    while (!spell.ready) await wait(50);
    const show = list => list.map(w => `${w}${spellKnown(w) ? "" : " -> " + (spellSuggest(w).slice(0, 3).join("/") || "?")}`).join(" | ");

    console.log("t-spellings (all must be flagged, th-form first):");
    console.log("  " + show(["metan", "metanol", "metyl", "metylamin", "dietylamin", "Etan", "etan", "eten", "etyn", "etyl", "etanol", "etansyre", "metylbenzen", "dietylether", "etylacetat", "Metanol"]));
    const ordinary = ["planeten", "kometen", "metal", "metallet", "meter", "metoden", "beten", "eten", "heten", "sætningen", "raketten", "etage", "etablere", "vetoen", "lætyl", "petanque", "Peter", "Retten", "detaljen", "metaller", "kompetent", "magneten", "atleten", "sketen", "Bethany"];
    console.log("ordinary words with 'et' (only 'eten' should be flagged):");
    console.log("  " + show(ordinary));
    console.log("chem rule: " + ["dienylamin", "diatylamin", "butadien", "hexadien", "propandiol", "hexandion", "dichlormethan"].map(w => `${w}=${spellChemical(w)}`).join(" "));

    const da = "diethylamin triethylamin methylamin ethanol methanol propanol butanol propanon ethanal methanal ethansyre eddikesyre myresyre svovlsyre saltsyre salpetersyre phosphorsyre kulsyre natriumchlorid natriumhydroxid kaliumpermanganat kaliumiodid kaliumdichromat calciumcarbonat natriumhydrogencarbonat ammoniumchlorid kobbersulfat jernoxid sølvnitrat bariumsulfat magnesiumoxid cyclohexan cyclohexen benzen methylbenzen dichlormethan tetrachlormethan trichlormethan chloroform ammoniak ethylacetat ethylethanoat diethylether acetylsalicylsyre benzoesyre aminosyre carboxylsyre aldehyd keton alkohol alkan alken alkyn hexan pentan heptan octan ethen ethyn propen glucose saccharose fructose phenolphthalein bromthymolblåt methylorange hydrogenperoxid natriumthiosulfat kaliumhexacyanoferrat tetraamminkobber hexaaquajern carbondioxid carbonmonoxid dinitrogenpentaoxid svovldioxid natriumchloridopløsning kaliumpermanganatopløsning";
    const en = "diethylamine triethylamine methylamine ethanol methanol propanol butanol propanone ethanal methanal ethanoic acetic formic sulfuric sulphuric hydrochloric nitric phosphoric sodium chloride hydroxide potassium permanganate iodide dichromate calcium carbonate hydrogencarbonate bicarbonate ammonium sulfate sulphate oxide nitrate cyclohexane cyclohexene benzene methylbenzene toluene dichloromethane tetrachloromethane trichloromethane chloroform ammonia ethyl ethanoate diethyl ether acetylsalicylic benzoic amino carboxylic aldehyde ketone alcohol alkane alkene alkyne hexane pentane heptane octane ethene ethyne propene glucose sucrose fructose phenolphthalein bromothymol methyl orange peroxide thiosulfate hexacyanoferrate tetraamminecopper hexaaquairon dioxide monoxide dinitrogen pentoxide";
    const typos = "beregnign koncentartion equilbrium molkeyle konstnaten hjemmeopgvae opløsnign temperatru reaktoin recieve seperate definately occured untill wierd bestemmmelse ligevægtskonstnat hastighde diethylamien cyclohexna hexnae methnol permanganta kaliumpermangant sulfrat ethanoik dichlormetahn bromthymolbalt".split(" ");
    for (const [name, list] of [["DA names", da], ["EN names", en]]) {
        const words = list.split(" "), bad = words.filter(w => !spellKnown(w));
        console.log(`${name}: ${words.length - bad.length}/${words.length} accepted ${bad.length ? "| flagged: " + bad.join(", ") : ""}`);
    }
    const missed = typos.filter(w => spellKnown(w));
    console.log(`typos caught: ${typos.length - missed.length}/${typos.length} ${missed.length ? "| missed: " + missed.join(", ") : ""}`);
    console.log("DONE");
})();
