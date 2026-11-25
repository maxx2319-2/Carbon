(async () => {
    const wait = ms => new Promise(r => setTimeout(r, ms));
    while (!spell.ready) await wait(50);
    for (const w of ["ligevægtskonstnat", "reaktionshastighde", "stofmængdekoncentartion", "titreringskruve", "opløsningsmidel", "hjemmeopgvae"]) console.log(`${w} -> ${spellSuggest(w).join(", ") || "(ingen forslag)"}`);
    console.log("DONE");
})();
