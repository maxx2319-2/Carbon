(async () => {
    const log = (...a) => console.log(a.join(" "));
    const step = message => new Promise(r => { window.resume = r; console.log(message); });
    const wait = ms => new Promise(r => setTimeout(r, ms));
    const center = (mf, w) => { const b = mf.getElementInfo(w.start + 2).bounds; return `${b.left + b.width / 2},${b.top + b.height / 2}`; };
    const flagged = mf => spellMisspelled(mf).map(w => w.text).join(", ") || "-";
    const squiggles = mf => mf.shadowRoot.querySelectorAll(".spell > div").length;
    try {
        const t = performance.now();
        while (!spell.ready && performance.now() - t < 20000) await wait(50);
        log(`0 dictionaries ready: ${spell.ready} after ${Math.round(performance.now() - t)} ms`);

        const mf = lines()[0], box = mf.getBoundingClientRect();
        await step(`LCLICK:${box.left + 20},${box.top + box.height / 2}`);
        await step("KEY:ctrl+2");
        log(`1 mode: ${modeOf(mf)}`);
        await step("TYPE:Vi skal beregne teh ");
        log(`2 typed:     ${rawOf(mf)}`);
        await step("KEY:ctrl+z");
        log(`3 ctrl+z:    ${rawOf(mf)} | flagged: ${flagged(mf)}`);
        await step("TYPE:.");
        log(`4 typed '.': ${rawOf(mf)}`);
        await step("TYPE: Den konstnaten og bestemmmelse ");
        log(`5 burst:     ${rawOf(mf)}`);
        await step("TYPE:med diethylamine, propan-2-ol og hjemmeopgvae,");
        log(`6 chem:      ${rawOf(mf)} | flagged: ${flagged(mf)} | squiggles: ${squiggles(mf)}`);

        await step("KEY:enter");
        const second = lines()[1];
        await step("TYPE:The equilbrium constant. ");
        log(`7 line 2:    ${rawOf(second)} (mode ${modeOf(second)}) | flagged: ${flagged(second)} | squiggles: ${squiggles(second)}`);

        const w = spellMisspelled(second, true)[0];
        await step(`RCLICK:${center(second, w)}`);
        log(`8 menu:      ${[...spellMenu.children].map(c => c.textContent || "---").join(" | ")}`);
        const item = spellMenu.children[0].getBoundingClientRect();
        await step(`LCLICK:${item.left + 10},${item.top + item.height / 2}`);
        log(`9 picked:    ${rawOf(second)} | menu: ${spellMenu.style.display}`);
        await step("KEY:ctrl+z");
        log(`10 ctrl+z:   ${rawOf(second)}`);

        await step("KEY:enter");
        const third = lines()[2];
        await step("KEY:ctrl+1");
        await step("TYPE:beregnign");
        log(`11 math line: mode ${modeOf(third)} | flagged: ${flagged(third)}`);
        second.focus();
        await wait(200);
        log(`12 squiggles per line: ${lines().map(squiggles).join(", ")}`);
    } catch (e) {
        log("ERROR " + e.stack);
    }
    console.log("DONE");
})();
