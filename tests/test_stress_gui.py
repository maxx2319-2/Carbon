import json
import os
import random
import re
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest

pytest.importorskip("PySide6")
import gui

SRC = Path(__file__).resolve().parent.parent / "src"

LATEX_TOKENS = [
    r"\frac{", "}{", "}", "{", r"\sqrt{", r"\sqrt[3]{", r"\left(", r"\right)", r"\cdot", "^{", "_{", r"\lbrack", r"\rbrack",
    r"\lbrace", r"\rbrace", r"\int", r"\differentialD", r"\sum_{", r"\lim_{", r"\to", r"\rightleftharpoons", "x", "k", "1", "2",
    "0.5", "=", ",", r"\placeholder{}", r"\textcolor{#569CD6}{", r"\mathbf{", r"\mathrm{", r"\pi", r"\mu", r"\#", r"\%",
    r"\:", r"\text{", "\\", r"\infty", r"\ln", r"\div", r"\le", "^{\\circ}", r"\mathrm{Løs}", r"\mathrm{Loop}", "Afstem",
]


def fuzz_latex(seed, count):
    rng = random.Random(seed)
    return ["".join(rng.choice(LATEX_TOKENS) for _ in range(rng.randint(1, 14))) for _ in range(count)]


@pytest.mark.parametrize("seed", range(3))
def test_fuzzed_latex_sheet_always_gives_rows(seed):
    lines = fuzz_latex(seed, 300)
    script = (
        "import json, quantity\n"
        "quantity.CACHE_FILE = quantity.BUNDLED_FILE\n"
        "import gui\n"
        f"lines = {lines!r}\n"
        "rows = json.loads(gui._InterpreterBridge().evaluate(json.dumps(lines)))\n"
        "ok = all(isinstance(r, list) and len(r) == 2 and r[0] in ('code', 'result', 'error', 'image', 'plot') and isinstance(r[1], str) for r in rows)\n"
        "print(json.dumps([ok, sum(1 for r in rows if r[0] == 'code')]))\n"
    )
    env = {**os.environ, "MPLBACKEND": "agg", "QT_QPA_PLATFORM": "offscreen", "PYTHONIOENCODING": "utf-8"}
    try:
        proc = subprocess.run([sys.executable, "-c", script], cwd=SRC, env=env, capture_output=True, text=True, encoding="utf-8", timeout=240)
    except subprocess.TimeoutExpired:
        pytest.fail("a fuzzed LaTeX sheet did not finish within 240 s")
    assert proc.returncode == 0, proc.stderr[-2000:]
    ok, code_rows = json.loads(proc.stdout.strip().splitlines()[-1])
    assert ok
    assert code_rows == len(lines)


def timed(f):
    t = time.perf_counter()
    f()
    return time.perf_counter() - t


@pytest.mark.xfail(reason="P-01: the fraction regex in calc_to_latex backtracks over the whole word, so long results take quadratic time", strict=True)
def test_calc_to_latex_handles_long_results_in_linear_time():
    small = timed(lambda: gui.calc_to_latex("A" * 4000))
    big = timed(lambda: gui.calc_to_latex("A" * 16000))
    assert big < 0.5
    assert big < small * 8


@pytest.mark.xfail(reason="C-02: load_regneark doesn't catch bad files, and at start-up that stops the program", strict=True)
@pytest.mark.parametrize("content", [b"", b"\x89PNG\r\n", b"{}", "{\"rows\": [[\"code\", \"\xe6\"]]}".encode("latin-1")])
def test_corrupt_regneark_file_does_not_raise(tmp_path, content):
    path = tmp_path / "bad.crbn"
    path.write_bytes(content)

    class Window:
        def new_interpreter_tab(self):
            raise AssertionError("a corrupt file should not open a tab")

    gui.MainWindow.load_regneark(Window(), str(path))


@pytest.mark.xfail(reason="C-06: a sheet that contains the word export is evaluated on the GUI thread", strict=True)
def test_export_sheet_is_not_evaluated_on_the_calling_thread():
    seen = {}
    bridge = gui._InterpreterBridge()

    def slow(data):
        seen["thread"] = threading.current_thread()
        time.sleep(0.5)
        return "[]"

    bridge.evaluate = slow
    bridge.run(1, json.dumps([r"\mathrm{BjerrumDiagram}\left(4,export\right)"]))
    deadline = time.time() + 5
    while "thread" not in seen and time.time() < deadline:
        time.sleep(0.05)
    assert seen["thread"] is not threading.current_thread()


@pytest.mark.xfail(reason="R-05: charges are written as ^{2}^{+}, a double superscript", strict=True)
def test_redox_result_has_valid_superscripts():
    rows = json.loads(gui._InterpreterBridge().evaluate(json.dumps([r"\mathrm{Afstem}\left(MnO_4^-+Fe^{2+}\to Mn^{2+}+Fe^{3+},syre\right)"])))
    assert not re.search(r"\^\{[^{}]*\}\^", rows[1][1])


@pytest.mark.xfail(reason="R-06: calc_to_latex wraps lists in \\mathrm{...}, so their braces vanish", strict=True)
def test_list_result_keeps_its_braces():
    rows = json.loads(gui._InterpreterBridge().evaluate(json.dumps([r"s=\lbrace1,2,3\rbrace"])))
    assert r"\{" in rows[1][1] or r"\lbrace" in rows[1][1]


@pytest.mark.xfail(reason="B-18: ev() splits with splitlines(), which also breaks at U+2028, so later results move to the wrong lines", strict=True)
def test_results_stay_on_their_own_lines():
    rows = json.loads(gui._InterpreterBridge().evaluate(json.dumps(["1+1 2+2", "5", "7"])))
    results = [rows[i + 1][1] for i, row in enumerate(rows) if row[0] == "code" and i + 1 < len(rows) and rows[i + 1][0] != "code"]
    assert results[1].endswith(r"\mathrm{5.0}") and results[2].endswith(r"\mathrm{7.0}")


@pytest.mark.xfail(reason="C-05: an exception while turning results into LaTeX escapes evaluate(), so the whole run shows nothing", strict=True)
def test_one_unprintable_result_does_not_hide_the_others():
    rows = json.loads(gui._InterpreterBridge().evaluate(json.dumps(["x=1", "integrate(x,x)+10^5000", "x+1"])))
    assert ["result", r"\Rightarrow\:\mathrm{2.0}"] in rows


@pytest.mark.xfail(reason="B-21: sqrt of a negative number gives a Python complex number like (1.2e-16+2j)", strict=True)
def test_square_root_of_negative_number_is_an_error():
    rows = json.loads(gui._InterpreterBridge().evaluate(json.dumps([r"\sqrt{-4}"])))
    assert rows[1][0] == "error"


@pytest.mark.xfail(reason="M-03: LaTeX commands MathLive can produce are not translated", strict=True)
@pytest.mark.parametrize("latex", [r"\ln\left(2\right)", r"6\div3", r"\sqrt[3]{8}", r"25\lbrack^{\circ}C\rbrack"])
def test_common_latex_commands_are_understood(latex):
    rows = json.loads(gui._InterpreterBridge().evaluate(json.dumps([latex])))
    assert rows[1][0] == "result"
