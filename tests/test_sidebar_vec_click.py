import json
import re

import pytest

from path import resource_path
from test_regneark_editor import js, pump, sheet, view

SOURCE = resource_path("src/gui.py").read_text(encoding="utf-8")
BLOCK = SOURCE[SOURCE.index('("Vektorer",symbol_grid(['):]
BLOCK = BLOCK[:BLOCK.index("])")]
LATEX = re.findall(r'\(\s*"[^"]*"\s*,\s*r"([^"]*)"\s*\)', BLOCK)

REACH = """
(() => {
  const mf = lines()[0];
  const r = mf.getBoundingClientRect();
  const hits = new Set();
  for (let y = r.top; y < r.bottom; y += 2)
    for (let x = r.left; x < r.left + 400; x += 2)
      hits.add(mf.getOffsetFromPoint(x, y));
  const holes = [];
  for (let i = 0; i <= mf.lastOffset; i++) {
    const a = mf._mathfield.model.at(i);
    if (a?.type === "placeholder" && a.parent?.command !== "\\\\hat") holes.push(i);
  }
  return JSON.stringify([holes, holes.filter(i => !hits.has(i))]);
})()
"""


SIDE = """
(() => {
  const mf = lines()[0];
  let base = null, sub = null;
  for (let i = 0; i <= mf.lastOffset; i++) {
    const a = mf._mathfield.model.at(i);
    const b = mf.getElementInfo(i)?.bounds;
    if (!b || a?.command !== "\\\\overrightarrow") continue;
    if (a.parentBranch === "subscript") sub = sub ?? b; else base = base ?? b;
  }
  return JSON.stringify([base.right, sub.left]);
})()
"""


@pytest.mark.parametrize("latex", [l for l in LATEX if "}_{" in l])
def test_subscript_sits_right_of_vector(view, latex):
    sheet(view, "", "2")
    js(view, f"insertLatex({json.dumps(latex)}); true")
    pump(200)
    base_right, sub_left = json.loads(js(view, SIDE))
    assert sub_left >= base_right - 1


def test_found_sidebar_entries():
    assert len(LATEX) == 13


@pytest.mark.parametrize("latex", [
    pytest.param(l, marks=pytest.mark.xfail(reason="MathLive cannot hit-test inside \\hat", strict=True)) if r"\hat" in l else l
    for l in LATEX
])
def test_every_vector_box_is_clickable_after_leaving(view, latex):
    sheet(view, "", "2")
    js(view, f"insertLatex({json.dumps(latex)}); true")
    pump(200)
    js(view, "focusLine(lines()[1]); true")
    pump(200)
    holes, unreachable = json.loads(js(view, REACH))
    assert holes
    assert unreachable == []
