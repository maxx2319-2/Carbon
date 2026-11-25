(async () => {
    const log = (...a) => console.log(a.join(" "));
    const step = message => new Promise(r => { window.resume = r; console.log(message); });
    const wait = ms => new Promise(r => setTimeout(r, ms));
    const squiggles = mf => mf.shadowRoot.querySelectorAll(".spell > div").length;
    try {
        while (!spell.ready) await wait(50);
        const mf = lines()[0], box = mf.getBoundingClientRect();
        await step(`LCLICK:${box.left + 20},${box.top + box.height / 2}`);
        await step("KEY:ctrl+2");
        await step("SLOW:Vi har diethyloid");
        await wait(200);
        log(`caret right after the word: flagged=${spellMisspelled(mf).map(w => w.text).join(", ") || "-"} squiggles=${squiggles(mf)}`);
        await step("SLOW: her");
        await wait(200);
        log(`after typing on:            flagged=${spellMisspelled(mf).map(w => w.text).join(", ") || "-"} squiggles=${squiggles(mf)}`);
        await step("KEY:enter");
        await step("SLOW:Diethyloid er ");
        await wait(200);
        const second = lines()[1];
        log(`capitalised at line start:   flagged=${spellMisspelled(second).map(w => w.text).join(", ") || "-"} squiggles=${squiggles(second)}`);
    } catch (e) {
        log("ERROR " + e.stack);
    }
    console.log("DONE");
})();
