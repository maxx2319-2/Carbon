import json
import re
from pathlib import Path

import pytest

pytest.importorskip("PySide6")
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from PySide6.QtWidgets import QApplication, QPushButton

import chem
import gui
import interpreter
import utils


HTML = Path(__file__).resolve().parent.parent / "Assets_math_live" / "regneark.html"
SAFE_JS = re.compile(re.search(r"const SAFE_JS = /(.*)/;", HTML.read_text(encoding="utf-8")).group(1))


def bjerrum(args):
    return interpreter.EV().ev(f"BjerrumDiagram({args})").get(0, "")


def test_returns_interactive_plot():
    plot = bjerrum("4.75")
    assert isinstance(plot, utils.FunctionPlot)
    assert (plot.start, plot.end) == (0, 14)
    assert plot.pks == [4.75]
    assert plot.functions[0]["label"] == r"\text{pKs: 4.75}"


@pytest.mark.parametrize("args", ["2.15, 7.20, 12.35", "4.75", "0.5, 13.9"])
def test_js_passes_safe_check(args):
    for f in bjerrum(args).functions:
        assert SAFE_JS.fullmatch(f["js"]), f["js"]


@pytest.mark.parametrize("pks", [2.15, 4.75, 9.25])
def test_curve_is_half_at_pks(pks):
    js = bjerrum(str(pks)).functions[0]["js"]
    f = eval("lambda x: " + js.replace("Math.pow", "pow"))
    assert f(pks) == pytest.approx(0.5)
    assert f(pks - 2) > 0.99
    assert f(pks + 2) < 0.01


def test_acid_names_still_work():
    name, value = next(iter(chem.pKa_values.items()))
    assert bjerrum(name).pks == [float(value)]


def test_bridge_sends_plot_row_not_image():
    rows = json.loads(gui._InterpreterBridge().evaluate(json.dumps([r"BjerrumDiagram\left(4.75\right)"])))
    kinds = [kind for kind, _ in rows]
    assert "plot" in kinds and "image" not in kinds
    data = json.loads(next(raw for kind, raw in rows if kind == "plot"))
    assert (data["start"], data["end"]) == (0, 14)


def test_panel_still_shows_matplotlib_figure(monkeypatch):
    QApplication.instance() or QApplication([])
    body = gui.bjerrum_panel()
    body.findChild(gui.MathInput).setText("4.75")
    next(b for b in body.findChildren(QPushButton) if b.text() == "Beregn").click()
    canvases = body.findChildren(FigureCanvasQTAgg)
    assert len(canvases) == 1
    assert canvases[0].figure.axes[0].lines[0].get_label() == "pKs: 4.75"
