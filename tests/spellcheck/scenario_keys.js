(async () => {
    const log = (...a) => console.log(a.join(" "));
    const step = message => new Promise(r => { window.resume = r; console.log(message); });
    const center = (mf, w) => { const b = mf.getElementInfo(w.start + 2).bounds; return `${b.left + b.width / 2},${b.top + b.height / 2}`; };
    const flagged = mf => misspelled(mf).map(w => w.text).join(", ") || "-";
    try {
        await window.spellReady;
        for (const w of ["beregnign", "koncentartion", "equilbrium", "molkeyle", "ligevægtskonstnat", "hjemmeopgvae"]) log(`suggest ${w} -> ${suggest(w).join(", ")}`);

        const ls = lines(), mf = ls[5];
        const box = mf.getBoundingClientRect();
        await step(`LCLICK:${box.left + 20},${box.top + box.height / 2}`);
        await step("TYPE:Vi skal beregne teh ");
        log(`1 typed fast:        ${mf.value}`);
        await step("KEY:ctrl+z");
        log(`2 ctrl+z:            ${mf.value} | flagged: ${flagged(mf)}`);
        await step("TYPE:.");
        log(`3 typed '.':         ${mf.value} (undone fix must not come back)`);
        await step("TYPE: Den konstnaten. ");
        log(`4 burst 'konstnaten. ': ${mf.value}`);
        await step("TYPE:Og hjemmeopgvae");
        log(`5 still typing:      ${mf.value} | flagged: ${flagged(mf)}`);
        await step("TYPE:,");
        log(`6 after ',':         ${mf.value} | flagged: ${flagged(mf)}`);

        const first = ls[0], w = misspelled(first, true)[0];
        await step(`RCLICK:${center(first, w)}`);
        log(`7 menu: ${[...menu.children].map(c => c.textContent || "---").join(" | ")}`);
        const item = menu.children[0].getBoundingClientRect();
        await step(`LCLICK:${item.left + 10},${item.top + item.height / 2}`);
        log(`8 picked:            ${first.value}`);
        await step("KEY:ctrl+z");
        log(`9 ctrl+z:            ${first.value}`);

        const third = ls[2], w3 = misspelled(third, true)[0];
        await step(`RCLICK:${center(third, w3)}`);
        log(`10 menu: ${[...menu.children].map(c => c.textContent || "---").join(" | ")}`);
    } catch (e) {
        log("ERROR " + e.stack);
    }
    console.log("DONE");
})();
