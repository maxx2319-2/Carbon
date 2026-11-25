(async () => {
    const wait = ms => new Promise(r => setTimeout(r, ms));
    while (!spell.ready) await wait(50);
    const flag = "diethyliod methylchlor ethylbrom diethylfluor methylcyan dimethylnitro ethylamino".split(" ");
    const ok = "diethyliodid iodmethan chlormethan brommethan methyliodid ethylbromid iodsyre aminosyre nitrobenzen hydroxybenzen chlorbenzen fluorbenzen bromthymolblåt hydrochloric thiosulfat cyanid iod jod chlor brom fluor dimethylsulfoxid sulfoxid dimethylsulfoxide".split(" ");
    console.log(`must be flagged: ${flag.filter(w => !spellKnown(w)).length}/${flag.length} ${flag.filter(w => spellKnown(w)).map(w => "| NOT FLAGGED " + w).join(" ")}`);
    console.log(`must be accepted: ${ok.filter(w => spellKnown(w)).length}/${ok.length} ${ok.filter(w => !spellKnown(w)).map(w => "| FLAGGED " + w).join(" ")}`);
    for (const w of ["diethyliod", "methylchlor", "dimetylsulfoxid", "dimethylsulfxid"]) console.log(`${w} -> ${spellSuggest(w).join(", ") || "(ingen forslag)"}`);
    console.log("DONE");
})();
