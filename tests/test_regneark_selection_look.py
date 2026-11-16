import json

import pytest

from test_regneark_editor import js, pump, view

SETUP = r"""(() => { setSheet([['code','abc'],['code',''],['code','\\frac{1}{2}'],['code','de']]); const L = lines(); sel = {anchor:{mf:L[0],offset:1}, focus:{mf:L[3],offset:1}}; paint(); return true; })()"""

RECTS = r"""JSON.stringify(lines().slice(0,4).map(mf => {
    const h = mf.getBoundingClientRect();
    const c = mf.shadowRoot.querySelector('.ML__content');
    const a = getComputedStyle(c, '::after');
    return {
        row: [h.top, h.bottom],
        boxes: [...mf.shadowRoot.querySelectorAll('.ML__selection')].map(s => { const r = s.getBoundingClientRect(); return [r.top, r.bottom]; }),
        stub: a.content !== 'none' ? parseFloat(a.height) : null,
    };
}))"""


@pytest.fixture
def rows(view):
    js(view, SETUP)
    pump(500)
    yield json.loads(js(view, RECTS))
    js(view, "clearSel(); true")


def test_rows_touch(rows):
    for upper, lower in zip(rows, rows[1:]):
        assert upper["row"][1] == pytest.approx(lower["row"][0], abs=0.5)


def test_selection_boxes_fill_their_row(rows):
    for r in rows:
        for top, bottom in r["boxes"]:
            assert top == pytest.approx(r["row"][0], abs=0.5)
            assert bottom == pytest.approx(r["row"][1], abs=0.5)
    assert all(r["boxes"] for i, r in enumerate(rows) if i != 1)


def test_newline_stub_fills_its_row(rows):
    for r in rows[:3]:
        assert r["stub"] == pytest.approx(r["row"][1] - r["row"][0], abs=1.5)
    assert rows[3]["stub"] is None


def test_single_line_selection_is_unchanged(view):
    js(view, "setSheet([['code','abc']]); focusLine(lines()[0]); lines()[0].selection = {ranges: [[0, 2]]}; true")
    pump(400)
    mf_top, box_top = json.loads(js(view, "JSON.stringify([lines()[0].getBoundingClientRect().top, lines()[0].shadowRoot.querySelector('.ML__selection').getBoundingClientRect().top])"))
    assert box_top - mf_top > 5
