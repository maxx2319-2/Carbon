import json

from PySide6.QtCore import QPoint, Qt
from PySide6.QtTest import QTest

from test_regneark_editor import code, js, pump, sheet, view

FIND = """
(() => {
  const mf = lines()[0];
  const r = mf.getBoundingClientRect();
  const y = (r.top + r.bottom) / 2;
  for (let x = r.left; x < r.left + 200; x += 1)
    if (mf.getOffsetFromPoint(x, y) === %d) return JSON.stringify([x, y]);
  return "null";
})()
"""


def test_can_click_into_both_vector_boxes(view):
    sheet(view, "")
    js(view, r"insertLatex('\\overrightarrow{#?}\\times\\overrightarrow{#?}'); true")
    pump(300)
    x, y = json.loads(js(view, FIND % 6))
    QTest.mouseClick(view.focusProxy(), Qt.LeftButton, Qt.NoModifier, QPoint(int(x), int(y)))
    pump()
    QTest.keyClicks(view.focusProxy(), "b")
    pump()
    assert code(view) == [r"\overrightarrow{\placeholder{}}\times\overrightarrow{b}"]
