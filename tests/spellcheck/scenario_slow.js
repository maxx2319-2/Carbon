(async () => {
    const log = (...a) => console.log(a.join(" "));
    const step = message => new Promise(r => { window.resume = r; console.log(message); });
    const wait = ms => new Promise(r => setTimeout(r, ms));
    try {
        while (!spell.ready) await wait(50);
        const mf = lines()[0], box = mf.getBoundingClientRect();
        await step(`LCLICK:${box.left + 20},${box.top + box.height / 2}`);
        await step("KEY:ctrl+2");
        await step("SLOW:Den konstnaten og bestemmmelse untill teh ende. ");
        log(`slow typed: ${rawOf(mf)}`);
        await step("KEY:ctrl+z");
        log(`ctrl+z 1:   ${rawOf(mf)}`);
        await step("KEY:ctrl+z");
        log(`ctrl+z 2:   ${rawOf(mf)}`);
        log(`undo steps left: ${undoStack.length}`);
    } catch (e) {
        log("ERROR " + e.stack);
    }
    console.log("DONE");
})();
