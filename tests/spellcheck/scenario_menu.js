(async () => {
    const log = (...a) => console.log(a.join(" "));
    const step = message => new Promise(r => { window.resume = r; console.log(message); });
    const wait = ms => new Promise(r => setTimeout(r, ms));
    const center = (mf, w) => { const b = mf.getElementInfo(w.start + 2).bounds; return `${b.left + b.width / 2},${b.top + b.height / 2}`; };
    const open = () => spellMenu.style.display === "block" ? "OPEN" : "closed";
    try {
        while (!spell.ready) await wait(50);
        if (window.PATCH) {
            window.addEventListener("pointerdown", e => { if (!spellMenu.contains(e.target)) closeSpellMenu(); }, true);
            log("patched: listening to pointerdown");
        }
        const first = lines()[0], box = first.getBoundingClientRect();
        await step(`LCLICK:${box.left + 20},${box.top + box.height / 2}`);
        await step("KEY:ctrl+2");
        await step("TYPE:The equilbrium constant is here");
        await step("KEY:enter");
        await step("TYPE:Mere tekst paa linje to");
        await wait(200);
        const w = spellMisspelled(first, true)[0];
        const targets = [
            ["same line, other word", () => { const b = first.getElementInfo(first.lastOffset - 2).bounds; return `${b.left},${b.top + b.height / 2}`; }],
            ["other line", () => { const b = lines()[1].getBoundingClientRect(); return `${b.left + 30},${b.top + b.height / 2}`; }],
            ["empty space below", () => `400,450`],
            ["line number gutter", () => { const b = first.getBoundingClientRect(); return `${b.left - 20},${b.top + b.height / 2}`; }],
        ];
        for (const [name, where] of targets) {
            await step(`RCLICK:${center(first, w)}`);
            const before = open();
            await step(`LCLICK:${where()}`);
            log(`${name}: menu ${before} -> after click ${open()}`);
        }
        await step(`RCLICK:${center(first, w)}`);
        const item = spellMenu.children[0].getBoundingClientRect();
        await step(`LCLICK:${item.left + 10},${item.top + item.height / 2}`);
        log(`click on a suggestion still works: ${rawOf(first)} | menu ${open()}`);
    } catch (e) {
        log("ERROR " + e.stack);
    }
    console.log("DONE");
})();
